"""
app/fuzzing/fuzzer.py — QUIC & protocol security fuzzing engine.

Vectors and targets come from the user's FuzzRequest.
No hardcoded host or mutation parameters.
"""

from __future__ import annotations

import asyncio
import os
import random
import time
from typing import Any, Dict, List

from app.models.requests import FuzzRequest, FuzzerVector


async def run_fuzz(req: FuzzRequest) -> Dict[str, Any]:
    """
    Run each requested mutation vector against the user-supplied target.
    Returns an anomaly report per vector.
    """
    report: Dict[str, Any] = {
        "host":    req.host,
        "port":    req.port,
        "vectors": [],
        "summary": {},
    }

    tasks = [
        _run_vector(req.host, req.port, v, req.iterations_per_vector, req.timeout_seconds)
        for v in req.vectors
    ]
    vector_results = await asyncio.gather(*tasks, return_exceptions=True)

    survived = 0
    crashed  = 0
    for i, result in enumerate(vector_results):
        if isinstance(result, Exception):
            result = _error_vector(req.vectors[i], str(result))
        report["vectors"].append(result)
        survived += result.get("survived", 0)
        crashed  += result.get("crashed", 0)

    total = survived + crashed
    report["summary"] = {
        "total_mutations": total,
        "survived":        survived,
        "anomalies":       crashed,
        "anomaly_rate_pct": round(crashed / total * 100, 2) if total else 0,
    }
    return report


async def _run_vector(
    host: str,
    port: int,
    vector: FuzzerVector,
    iterations: int,
    timeout: float,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "vector":    vector.value,
        "iterations": iterations,
        "survived":  0,
        "crashed":   0,
        "anomalies": [],
    }

    mutator = _MUTATORS.get(vector, _generic_mutator)

    for i in range(iterations):
        payload = mutator(i)
        t0 = time.perf_counter()
        try:
            # Attempt to send the mutated payload as a raw UDP datagram (QUIC)
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, _udp_probe, host, port, payload),
                timeout=timeout,
            )
            result["survived"] += 1
        except asyncio.TimeoutError:
            result["crashed"] += 1
            result["anomalies"].append({
                "iteration": i,
                "type":      "timeout",
                "payload_hex": payload.hex()[:64],
                "elapsed_ms": round((time.perf_counter() - t0) * 1000, 2),
            })
        except Exception as e:
            result["crashed"] += 1
            result["anomalies"].append({
                "iteration": i,
                "type":      "exception",
                "error":     str(e)[:200],
                "payload_hex": payload.hex()[:64],
            })

    return result


def _udp_probe(host: str, port: int, payload: bytes) -> None:
    """Fire-and-forget UDP probe (blocking, run in executor)."""
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.settimeout(2)
        s.sendto(payload, (host, port))
        try:
            s.recvfrom(4096)
        except socket.timeout:
            pass


# ── Mutation functions ────────────────────────────────────────────────────────

def _stream_offset_overflow(iteration: int) -> bytes:
    """STREAM frame with overflowed offset field (varint max value)."""
    stream_id = iteration % 100
    offset    = 0x3FFFFFFFFFFFFFFF  # max 62-bit varint
    header    = bytes([0x0C | (0x04 if offset else 0)])
    return header + _encode_varint(stream_id) + _encode_varint(offset) + os.urandom(16)


def _ack_range_inflation(iteration: int) -> bytes:
    """ACK frame with range count exceeding packet space."""
    # ACK frame type 0x02
    frame  = bytes([0x02])
    frame += _encode_varint(iteration + 100)   # Largest Acknowledged
    frame += _encode_varint(0)                  # ACK Delay
    n_ranges = random.randint(100, 500)
    frame += _encode_varint(n_ranges)
    for _ in range(n_ranges):
        frame += _encode_varint(random.randint(1, 50))
        frame += _encode_varint(random.randint(0, 10))
    return frame


def _cid_truncation(iteration: int) -> bytes:
    """Long header with truncated (1-byte) connection ID instead of 8–20 bytes."""
    version      = (1).to_bytes(4, "big")
    dcid_len     = bytes([1])
    dcid         = os.urandom(1)
    scid_len     = bytes([1])
    scid         = os.urandom(1)
    long_header  = bytes([0xC0]) + version + dcid_len + dcid + scid_len + scid
    return long_header + os.urandom(random.randint(4, 32))


def _malformed_crypto_frame(iteration: int) -> bytes:
    """CRYPTO frame (0x06) with offset pointing beyond length."""
    offset = random.randint(0xFFFF, 0x3FFFFFFF)
    length = random.randint(1, 50)
    payload = os.urandom(length)
    return bytes([0x06]) + _encode_varint(offset) + _encode_varint(length) + payload


def _reset_storm(iteration: int) -> bytes:
    """Multiple RESET_STREAM frames in one datagram."""
    frames = b""
    for sid in range(min(iteration + 1, 20)):
        frames += bytes([0x04])
        frames += _encode_varint(sid)
        frames += _encode_varint(0)   # error code
        frames += _encode_varint(0)   # final size
    return frames or os.urandom(8)


def _zero_rtt_replay(iteration: int) -> bytes:
    """Replay a fabricated 0-RTT Initial packet."""
    version     = (1).to_bytes(4, "big")
    dcid        = os.urandom(8)
    scid        = os.urandom(8)
    token_len   = bytes([4])
    token       = os.urandom(4)
    long_header = (
        bytes([0xC0 | 0x01])   # Long header, 0-RTT type
        + version
        + bytes([len(dcid)]) + dcid
        + bytes([len(scid)]) + scid
        + token_len + token
    )
    return long_header + os.urandom(random.randint(32, 128))


def _generic_mutator(iteration: int) -> bytes:
    return os.urandom(random.randint(16, 128))


_MUTATORS = {
    FuzzerVector.STREAM_OFFSET_OVERFLOW: _stream_offset_overflow,
    FuzzerVector.ACK_RANGE_INFLATION:    _ack_range_inflation,
    FuzzerVector.CID_TRUNCATION:         _cid_truncation,
    FuzzerVector.MALFORMED_CRYPTO_FRAME: _malformed_crypto_frame,
    FuzzerVector.RESET_STORM:            _reset_storm,
    FuzzerVector.ZERO_RTT_REPLAY:        _zero_rtt_replay,
}


def _encode_varint(v: int) -> bytes:
    """QUIC variable-length integer encoding (RFC 9000 §16)."""
    if v < 0x40:
        return bytes([v])
    if v < 0x4000:
        return ((v | 0x4000) >> 8 & 0xFF).to_bytes(1, "big") + (v & 0xFF).to_bytes(1, "big")
    if v < 0x40000000:
        return (v | 0x80000000).to_bytes(4, "big")
    return (v | 0xC000000000000000).to_bytes(8, "big")


def _error_vector(vector: FuzzerVector, error: str) -> Dict[str, Any]:
    return {
        "vector":    vector.value,
        "iterations": 0,
        "survived":  0,
        "crashed":   0,
        "error":     error,
        "anomalies": [],
    }