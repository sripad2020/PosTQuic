import os
import time
import socket
import asyncio
from typing import Dict, Any, List

from app.protocols.quic_real import perform_zero_rtt_test, AIOQUIC_AVAILABLE
try:
    from app.protocols import quic_lab
except Exception:  # aioquic / cryptography unavailable
    quic_lab = None


def _lab_unavailable(host: str, port: int) -> Dict[str, Any]:
    return {"target": f"{host}:{port}", "status": "TEST_UNAVAILABLE",
            "verdict": "Could not run: aioquic failed to import (check the cryptography version pin)",
            "summary": [], "table": None}

_KNOWN_VERSIONS = {
    0x00000001: "QUIC v1 (RFC 9000)",
    0x6B3343CF: "QUIC v2 (RFC 9369)",
}


def _version_name(v: int) -> str:
    if v in _KNOWN_VERSIONS:
        name = _KNOWN_VERSIONS[v]
    elif v & 0x0F0F0F0F == 0x0A0A0A0A:
        name = "reserved/GREASE"
    elif v >> 8 == 0xFF0000:
        name = f"draft-{v & 0xFF}"
    else:
        name = "unknown"
    return f"0x{v:08x} ({name})"


def _parse_version_negotiation(data: bytes, our_dcid: bytes, our_scid: bytes) -> Dict[str, Any]:
    """Parse a Version Negotiation packet (RFC 9000 §17.2.1) and check that the
    server echoed our connection IDs back swapped (its DCID = our SCID)."""
    if len(data) < 7:
        return {"valid": False, "versions": [], "reason": "reply too short"}
    if not data[0] & 0x80:
        return {"valid": False, "versions": [], "reason": "not a long-header packet"}
    if data[1:5] != bytes(4):
        return {"valid": False, "versions": [], "reason": f"version field 0x{data[1:5].hex()} is not 0"}
    i = 5
    dlen = data[i]; i += 1
    dcid = data[i:i + dlen]; i += dlen
    if i >= len(data):
        return {"valid": False, "versions": [], "reason": "truncated"}
    slen = data[i]; i += 1
    scid = data[i:i + slen]; i += slen
    if dcid != our_scid or scid != our_dcid:
        return {"valid": False, "versions": [], "reason": "connection IDs not echoed back correctly"}
    body = data[i:]
    versions = [int.from_bytes(body[j:j + 4], "big") for j in range(0, len(body) - len(body) % 4, 4)]
    return {"valid": True, "versions": versions, "reason": ""}


class AdvancedQUICTestingEngine:

    # Helper: Measure real UDP RTT and socket response to target
    async def _udp_probe(self, host: str, port: int, payload_bytes: bytes, timeout: float = 2.0) -> Dict[str, Any]:
        t0 = time.perf_counter()
        try:
            ip = socket.gethostbyname(host)
        except Exception as e:
            return {
                "success": False,
                "ip": host,
                "rtt_ms": 0.0,
                "error": f"DNS Resolution failed for {host}: {str(e)}",
                "bytes_sent": 0,
                "bytes_recv": 0,
                "data": b""
            }

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        loop = asyncio.get_event_loop()

        try:
            await loop.sock_sendto(sock, payload_bytes, (ip, port))
            t_sent = time.perf_counter()
            data, addr = await asyncio.wait_for(loop.sock_recvfrom(sock, 2048), timeout=timeout)
            t_recv = time.perf_counter()
            rtt = (t_recv - t0) * 1000.0
            sock.close()
            return {
                "success": True,
                "ip": ip,
                "port": port,
                "rtt_ms": round(rtt, 2),
                "bytes_sent": len(payload_bytes),
                "bytes_recv": len(data),
                "data": data
            }
        except asyncio.TimeoutError:
            t_recv = time.perf_counter()
            rtt = (t_recv - t0) * 1000.0
            sock.close()
            return {
                "success": False,
                "ip": ip,
                "port": port,
                "rtt_ms": round(rtt, 2),
                "error": "UDP Probe Timeout (Host live, no UDP response received within timeout)",
                "bytes_sent": len(payload_bytes),
                "bytes_recv": 0,
                "data": b""
            }
        except Exception as e:
            sock.close()
            return {
                "success": False,
                "ip": ip,
                "port": port,
                "rtt_ms": 0.0,
                "error": str(e),
                "bytes_sent": len(payload_bytes),
                "bytes_recv": 0,
                "data": b""
            }

    # 1. 0-RTT resumption & ticket-reuse check (real aioquic handshakes)
    async def run_zerortt_replay_test(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        details = {
            "rfc_standard": "RFC 9001 Section 4.6 & RFC 8446 Section 8 — 0-RTT and Anti-Replay",
            "host_architecture": (
                "Three real QUIC connections via aioquic: (1) full handshake to obtain a session "
                "ticket, (2) resumption with that ticket offering 0-RTT, (3) a second resumption "
                "reusing the SAME ticket. This observes the server's 0-RTT and ticket-reuse policy; "
                "it does not send 0-RTT application data, so it is not a byte-for-byte replay attack."
            ),
            "packet_sequence": "Full handshake ➔ NewSessionTicket ➔ Resume #1 (0-RTT offer) ➔ Resume #2 (same ticket)",
        }
        base = {"target": f"{target_host}:{target_port}", "host_implementation_details": details}

        if not AIOQUIC_AVAILABLE:
            return {**base, "status": "ZERORTT_TEST_UNAVAILABLE",
                    "anti_replay_protection": "NOT_TESTED (aioquic could not be imported)",
                    "verdict": "Could not run: aioquic could not be imported",
                    "summary": [], "table": None,
                    "strike_register_status": "UNKNOWN", "flights_audit": []}

        res = await perform_zero_rtt_test(target_host, target_port)
        if not res.get("success"):
            return {**base, "status": "ZERORTT_TEST_FAILED",
                    "ip_address": res.get("ip_address"),
                    "error": res.get("error"),
                    "anti_replay_protection": f"NOT_TESTED ({res.get('error')})",
                    "verdict": f"Could not run: {res.get('error')}",
                    "summary": [], "table": None,
                    "strike_register_status": "UNKNOWN", "flights_audit": []}

        flights = [{
            "flight_id": 1,
            "packet_type": "Full 1-RTT handshake",
            "status": "TICKET_ISSUED" if res["ticket_issued"] else "NO_TICKET",
            "rtt_ms": res["initial_handshake_ms"],
            "server_action": (
                f"Handshake in {res['initial_handshake_ms']} ms. "
                + (f"Ticket lifetime {res.get('ticket_lifetime_s')}s, "
                   f"max_early_data={res.get('ticket_max_early_data')}"
                   if res["ticket_issued"] else "Server sent no NewSessionTicket.")
            ),
        }]

        def _flight(fid: int, label: str, r: Dict[str, Any]) -> Dict[str, Any]:
            if not r.get("connected"):
                return {"flight_id": fid, "packet_type": label, "status": "CONNECT_FAILED",
                        "server_action": r.get("error", "unknown error")}
            if r["early_data_accepted"]:
                status = "0RTT_ACCEPTED"
            elif r["early_data_offered"]:
                status = "0RTT_REJECTED"
            elif r["session_resumed"]:
                status = "RESUMED_NO_0RTT"
            else:
                status = "FULL_HANDSHAKE"
            return {"flight_id": fid, "packet_type": label, "status": status,
                    "rtt_ms": r["handshake_ms"],
                    "server_action": (f"Handshake {r['handshake_ms']} ms | resumed={r['session_resumed']} | "
                                      f"0-RTT offered={r['early_data_offered']} accepted={r['early_data_accepted']}")}

        if not res["ticket_issued"]:
            verdict, register = "NO_RESUMPTION (server issued no session ticket, so 0-RTT is impossible)", "N/A"
        else:
            r1, r2 = res["resume_1"], res["resume_2_same_ticket"]
            flights.append(_flight(2, "Resume #1 with ticket (0-RTT offered)", r1))
            flights.append(_flight(3, "Resume #2 reusing the SAME ticket", r2))
            a1, a2 = r1.get("early_data_accepted"), r2.get("early_data_accepted")
            if res.get("ticket_max_early_data") is None:
                verdict, register = "0RTT_DISABLED (ticket does not permit early data)", "N/A"
            elif not (r1.get("connected") and r2.get("connected")):
                verdict, register = "INCONCLUSIVE (a resumption connection failed)", "UNKNOWN"
            elif a1 and a2:
                verdict = "TICKET_REUSE_ACCEPTED (same ticket accepted for 0-RTT twice; replay safety relies on the application)"
                register = "NOT_ENFORCED"
            elif a1 and not a2:
                verdict, register = "SINGLE_USE_TICKET (0-RTT accepted once, rejected on reuse)", "ENFORCED"
            else:
                verdict, register = "0RTT_REJECTED (server declined early data)", "N/A"

        return {
            **base,
            "status": "ZERORTT_TEST_COMPLETE",
            "engine": "aioquic (real QUIC handshakes)",
            "ip_address": res.get("ip_address"),
            "measured_rtt_ms": res["initial_handshake_ms"],
            "anti_replay_protection": verdict,
            "strike_register_status": register,
            "flights_audit": flights,
            "verdict": verdict,
            "summary": [
                ["Session ticket issued", "yes" if res["ticket_issued"] else "no"],
                ["Ticket max_early_data", res.get("ticket_max_early_data")],
                ["Ticket lifetime", f"{res.get('ticket_lifetime_s')} s"],
                ["Single-use enforcement", register],
            ],
            "table": {"columns": ["#", "Connection", "Result", "Details"],
                      "rows": [[f["flight_id"], f["packet_type"], f["status"], f["server_action"]]
                               for f in flights]},
        }

    # 2. QPACK header compression (real test — see app/protocols/quic_lab.py)
    async def run_qpack_analysis(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.qpack_analysis(target_host, target_port)

    # 3. Congestion control (real test — see app/protocols/quic_lab.py)
    async def run_congestion_benchmark(self, target_host: str, target_port: int = 4433, algorithm: str = "cubic") -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.congestion_benchmark(target_host, target_port, algorithm=algorithm)

    # 4. Path MTU & ECN (real test — see app/protocols/quic_lab.py)
    async def run_pmtud_ecn_probe(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.pmtud_probe(target_host, target_port)

    # 5. Spin bit & connection-ID privacy (real test — see app/protocols/quic_lab.py)
    async def run_spinbit_cid_privacy_audit(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.spinbit_cid_audit(target_host, target_port)

    # 6. Connection migration (real test — see app/protocols/quic_lab.py)
    async def run_connection_migration_test(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.connection_migration(target_host, target_port)

    # 7. DATAGRAM extension (real test — see app/protocols/quic_lab.py)
    async def run_datagram_extension_test(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.datagram_extension(target_host, target_port)

    # 8. ECH / SNI privacy (real test — see app/protocols/quic_lab.py)
    async def run_ech_sni_privacy_test(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.ech_check(target_host, target_port)

    # 9. Flow control (real test — see app/protocols/quic_lab.py)
    async def run_flow_control_autotune_test(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.flow_control(target_host, target_port)

    # 10. ACK behaviour (real test — see app/protocols/quic_lab.py)
    async def run_ack_frequency_test(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.ack_behaviour(target_host, target_port)

    # 11. Stateless reset (real test — see app/protocols/quic_lab.py)
    async def run_stateless_reset_test(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.stateless_reset(target_host, target_port)

    # 12. Version Negotiation & Downgrade Protection (Real Invalid Version Probe)
    async def run_version_negotiation_test(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        # 0x?a?a?a?a versions are reserved (RFC 9000 §15) so that any compliant
        # server MUST answer with a Version Negotiation packet listing what it supports.
        offered = 0x1A2A3A4A
        dcid, scid = os.urandom(8), os.urandom(8)
        packet = (bytes([0xC0]) + offered.to_bytes(4, "big")
                  + bytes([len(dcid)]) + dcid + bytes([len(scid)]) + scid)
        # Servers may ignore datagrams under 1200 bytes (RFC 9000 §14.1), so pad.
        packet += b"\x00" * (1200 - len(packet))

        res = await self._udp_probe(target_host, target_port, packet)
        parsed = _parse_version_negotiation(res.get("data", b""), dcid, scid)

        supported = [_version_name(v) for v in parsed["versions"]] if parsed["valid"] else []
        if parsed["valid"]:
            status = "VERSION_NEGOTIATION_PACKET_RECEIVED"
            negotiated = supported[0] if supported else "none listed"
        elif res["bytes_recv"] > 0:
            status = f"UNEXPECTED_REPLY ({parsed['reason']})"
            negotiated = "unknown"
        else:
            status = "NO_REPLY (server does not speak QUIC on this port, or UDP is blocked)"
            negotiated = "unknown"

        return {
            "status": "VERSION_NEGOTIATION_TEST_COMPLETE",
            "target": f"{target_host}:{target_port}",
            "ip_address": res.get("ip"),
            "offered_version": f"0x{offered:08x} (reserved, forces negotiation)",
            "negotiated_version": negotiated,
            "socket_response_bytes": res["bytes_recv"],
            "socket_rtt_ms": res["rtt_ms"],
            "supported_versions": supported,
            "connection_ids_echoed_correctly": parsed["valid"],
            "downgrade_prevention_status": status,
            "verdict": (f"Server supports: {', '.join(supported)}" if parsed["valid"] else status),
            "summary": [
                ["Offered version", f"0x{offered:08x} (reserved)"],
                ["Reply", f"{res['bytes_recv']} B in {res['rtt_ms']} ms" if res["bytes_recv"] else "none"],
                ["Connection IDs echoed correctly", "yes" if parsed["valid"] else "no"],
            ],
            "table": {"columns": ["Supported version"], "rows": [[v] for v in supported]},
            "host_implementation_details": {
                "rfc_standard": "RFC 9000 Section 6 & 17.2.1 — Version Negotiation",
                "host_architecture": (
                    "Sends a padded 1200-byte Initial with a reserved version. A compliant server replies "
                    "with a Version Negotiation packet (version 0x00000000) that swaps our connection IDs "
                    "and lists its supported versions; the list above is parsed from that live reply."
                ),
            },
        }

    # 13. CRYPTO reassembly (real test — see app/protocols/quic_lab.py)
    async def run_crypto_stream_reassembly_test(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.crypto_reassembly(target_host, target_port)

    # 14. Multipath QUIC (real test — see app/protocols/quic_lab.py)
    async def run_multipath_quic_test(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.multipath(target_host, target_port)

    # 15. WebTransport over HTTP/3 (real test — see app/protocols/quic_lab.py)
    async def run_webtransport_protocol_test(self, target_host: str, target_port: int = 4433) -> Dict[str, Any]:
        if quic_lab is None:
            return _lab_unavailable(target_host, target_port)
        return await quic_lab.webtransport(target_host, target_port)


adv_quic_engine_instance = AdvancedQUICTestingEngine()

