"""Real QUIC experiments for the Advanced QUIC lab, built on aioquic.

Every test opens genuine QUIC connections and derives its result from what
actually happened: qlog events recorded by aioquic, the transport parameters
and HTTP/3 settings the server really sent, and real UDP replies. Anything
aioquic cannot do is reported as NOT_SUPPORTED instead of being simulated.

All tests return the same shape so the UI can render them generically:
    status   - machine-readable outcome
    verdict  - one-line human summary
    summary  - list of [label, value] pairs (measured values)
    table    - optional {"columns": [...], "rows": [[...], ...]}
"""
import asyncio
import functools
import os
import socket
import ssl
import sys
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from aioquic.asyncio.client import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.h3.connection import H3_ALPN, H3Connection
from aioquic.h3.events import DataReceived, HeadersReceived
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import ConnectionTerminated, QuicEvent
from aioquic.quic.logger import QuicLogger

DEFAULT_TIMEOUT = 8.0


# --------------------------------------------------------------------------
# Connection plumbing
# --------------------------------------------------------------------------
class _HiResLoop:
    """Event-loop wrapper that gives aioquic a high-resolution clock.

    aioquic timestamps every packet with loop.time(). On Windows with
    Python < 3.13 that is GetTickCount64 (15.6 ms resolution), which rounds
    every RTT sample to 0 or 15.6 ms. perf_counter has ~100 ns resolution.
    Timers are converted back to relative delays on the real loop."""

    def __init__(self, loop):
        self._real = loop

    def time(self) -> float:
        return time.perf_counter()

    def call_at(self, when, callback, *args):
        return self._real.call_later(max(0.0, when - time.perf_counter()), callback, *args)

    def __getattr__(self, name):
        return getattr(self._real, name)


class LabProtocol(QuicConnectionProtocol):
    """QUIC protocol with an optional HTTP/3 layer, byte counters and a hook to
    send the first flight out of order. It never creates asyncio stream
    readers/writers, so peer-initiated HTTP/3 control streams don't produce
    'StreamWriter.__del__' noise."""

    def __init__(self, *args, h3: bool = True, webtransport: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self._loop = _HiResLoop(self._loop)
        self.h3 = H3Connection(self._quic, enable_webtransport=webtransport) if h3 else None
        self._waiters: Dict[int, Dict[str, Any]] = {}
        self.bytes_sent = self.bytes_recv = 0
        self.datagrams_sent = self.datagrams_recv = 0
        self.reverse_first_flight = False
        self.first_flight_sizes: List[int] = []
        self._first_flight_done = False
        self.handshake_ms: float = 0.0
        self.terminated: Optional[ConnectionTerminated] = None

    # -- I/O -------------------------------------------------------------
    def transmit(self) -> None:
        # Same as QuicConnectionProtocol.transmit, plus counting and optional
        # reordering of the very first flight.
        self._transmit_task = None
        datagrams = self._quic.datagrams_to_send(now=self._loop.time())
        if datagrams and not self._first_flight_done:
            self._first_flight_done = True
            self.first_flight_sizes = [len(d) for d, _ in datagrams]
            if self.reverse_first_flight and len(datagrams) > 1:
                datagrams = list(reversed(datagrams))
        for data, addr in datagrams:
            self.bytes_sent += len(data)
            self.datagrams_sent += 1
            self._transport.sendto(data, addr)
        timer_at = self._quic.get_timer()
        if self._timer is not None and self._timer_at != timer_at:
            self._timer.cancel()
            self._timer = None
        if self._timer is None and timer_at is not None:
            self._timer = self._loop.call_at(timer_at, self._handle_timer)
        self._timer_at = timer_at

    def datagram_received(self, data, addr) -> None:
        self.bytes_recv += len(data)
        self.datagrams_recv += 1
        super().datagram_received(data, addr)

    # -- events ----------------------------------------------------------
    def quic_event_received(self, event: QuicEvent) -> None:
        if isinstance(event, ConnectionTerminated):
            self.terminated = event
            for w in self._waiters.values():
                if not w["fut"].done():
                    w["fut"].set_exception(ConnectionError(
                        f"connection closed by peer: {event.reason_phrase or event.error_code}"))
            self._waiters.clear()
        if self.h3 is None:
            return
        for ev in self.h3.handle_event(event):
            sid = getattr(ev, "stream_id", None)
            w = self._waiters.get(sid)
            if w is None:
                continue
            w["events"].append(ev)
            done = getattr(ev, "stream_ended", False) or (
                w["headers_only"] and isinstance(ev, HeadersReceived))
            if done and not w["fut"].done():
                self._waiters.pop(sid, None)
                w["fut"].set_result(w["events"])

    def request(self, headers, body: bytes = b"", headers_only: bool = False):
        """Send an HTTP/3 request; returns (stream_id, future of H3 events)."""
        sid = self._quic.get_next_available_stream_id()
        self.h3.send_headers(sid, headers, end_stream=not body and not headers_only)
        if body:
            self.h3.send_data(sid, body, end_stream=True)
        fut = self._loop.create_future()
        # Mark a later exception as retrieved, so requests still pending when
        # the session closes don't log "Future exception was never retrieved".
        fut.add_done_callback(lambda f: f.cancelled() or f.exception())
        self._waiters[sid] = {"events": [], "fut": fut, "headers_only": headers_only}
        self.transmit()
        return sid, fut

    async def timed_ping(self, timeout: float = 3.0) -> float:
        t0 = time.perf_counter()
        await asyncio.wait_for(self.ping(), timeout)
        return round((time.perf_counter() - t0) * 1000.0, 2)

    # -- qlog helpers ------------------------------------------------------
    def events(self, name: Optional[str] = None) -> List[dict]:
        trace = self._quic._quic_logger
        evs = list(trace._events) if trace is not None else []
        return [e for e in evs if name is None or e["name"] == name]

    def remote_params(self) -> Dict[str, Any]:
        for e in self.events("transport:parameters_set"):
            if e["data"].get("owner") == "remote":
                return e["data"]
        return {}

    def frames(self, direction: str, frame_type: Optional[str] = None):
        """Yield (event, frame) for frames sent ('sent') or received ('received')."""
        for e in self.events(f"transport:packet_{direction}"):
            for f in e["data"].get("frames", []):
                if frame_type is None or f.get("frame_type") == frame_type:
                    yield e, f


@asynccontextmanager
async def lab_session(host: str, port: int, *, timeout: float = DEFAULT_TIMEOUT,
                      alpn: Optional[List[str]] = None, h3: bool = True,
                      webtransport: bool = False, configure=None, before_connect=None):
    config = QuicConfiguration(is_client=True, alpn_protocols=alpn or list(H3_ALPN))
    config.server_name = host
    config.verify_mode = ssl.CERT_NONE
    config.quic_logger = QuicLogger()
    if configure:
        configure(config)
    factory = functools.partial(LabProtocol, h3=h3, webtransport=webtransport)
    t0 = time.perf_counter()
    async with connect(host, port, configuration=config, create_protocol=factory,
                       wait_connected=False) as proto:
        if before_connect:
            before_connect(proto)
        # connect(wait_connected=False) does not send the Initial on its own.
        proto.transmit()
        await asyncio.wait_for(proto.wait_connected(), timeout)
        proto.handshake_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        yield proto


def _req_headers(method: str, host: str, path: str, extra=()) -> list:
    return [(b":method", method.encode()), (b":scheme", b"https"),
            (b":authority", host.encode()), (b":path", path.encode()),
            (b"user-agent", b"QUICLAB/1.0")] + list(extra)


async def _await_settings(p: LabProtocol, timeout: float = 2.0) -> Dict[int, int]:
    end = time.perf_counter() + timeout
    while p.h3.received_settings is None and time.perf_counter() < end:
        await asyncio.sleep(0.05)
    return p.h3.received_settings or {}


def _status_of(events) -> Optional[str]:
    for ev in events:
        if isinstance(ev, HeadersReceived):
            for k, v in ev.headers:
                if k == b":status":
                    return v.decode()
    return None


def _resolve_v4(host: str) -> str:
    return socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_DGRAM)[0][4][0]


def _kb(n) -> str:
    return f"{n / 1024:.1f} KB" if n is not None else "n/a"


def _mb(n) -> str:
    return f"{n / 1048576:.2f} MB" if n is not None else "not sent"


# --------------------------------------------------------------------------
# Result wrapper
# --------------------------------------------------------------------------
def lab_test(rfc: str, how: str, sequence: str = ""):
    """Wrap a test: adds target + RFC details, converts errors into results."""
    def deco(fn):
        @functools.wraps(fn)
        async def inner(host: str, port: int, **kw) -> Dict[str, Any]:
            base = {"target": f"{host}:{port}",
                    "host_implementation_details": {"rfc_standard": rfc, "host_architecture": how,
                                                    "packet_sequence": sequence}}
            try:
                res = await fn(host, port, **kw)
            except asyncio.TimeoutError:
                res = _failed("timed out (no QUIC handshake/answer from the server on this port)")
            except Exception as e:  # noqa: BLE001 - report every failure honestly
                res = _failed(f"{type(e).__name__}: {e}")
            return {**base, **res}
        return inner
    return deco


def _failed(reason: str) -> Dict[str, Any]:
    return {"status": "TEST_FAILED", "verdict": f"Could not run: {reason}",
            "error": reason, "summary": [], "table": None}


# --------------------------------------------------------------------------
# 2. QPACK
# --------------------------------------------------------------------------
@lab_test("RFC 9204 — QPACK Header Compression for HTTP/3",
          "Sends two identical real HTTP/3 GET requests. Encoded header-block sizes come from aioquic's "
          "qlog (frame_created / frame_parsed); raw sizes are the sum of name+value bytes. Encoder-stream "
          "bytes show whether the server inserted entries into our dynamic table.",
          "Handshake ➔ SETTINGS exchange ➔ GET #1 ➔ GET #2 (same headers) ➔ compare sizes")
async def qpack_analysis(host: str, port: int, path: str = "/") -> Dict[str, Any]:
    async with lab_session(host, port) as p:
        settings = await _await_settings(p)
        rows, statuses = [], []
        for n in (1, 2):
            enc_in_before = p.h3._encoder_bytes_received
            sid, fut = p.request(_req_headers("GET", host, path))
            evs = await asyncio.wait_for(fut, DEFAULT_TIMEOUT)
            statuses.append(_status_of(evs))
            enc_in = p.h3._encoder_bytes_received - enc_in_before
            for name, direction in (("http:frame_created", "request"), ("http:frame_parsed", "response")):
                for e in p.events(name):
                    d = e["data"]
                    if d.get("stream_id") == sid and d.get("frame", {}).get("frame_type") == "headers":
                        hdrs = d["frame"]["headers"]
                        raw = sum(len(h["name"]) + len(h["value"]) for h in hdrs)
                        enc = d.get("length", 0)
                        rows.append([f"#{n}", direction, len(hdrs), raw, enc,
                                     f"{round((1 - enc / raw) * 100, 1) if raw else 0}%",
                                     enc_in if direction == "response" else "—"])
                        break
        resp = [r for r in rows if r[1] == "response"]
        dyn_bytes = p.h3._encoder_bytes_received
        verdict = (f"Response headers {resp[0][3]} B ➔ {resp[0][4]} B on request #1, "
                   f"{resp[-1][4]} B on request #2" if resp else "No response headers received")
        if dyn_bytes:
            verdict += f"; server used our dynamic table ({dyn_bytes} B on its encoder stream)"
        else:
            verdict += "; server used only the static table / literals (no dynamic-table inserts)"
        raw_total = sum(r[3] for r in rows)
        enc_total = sum(r[4] for r in rows)
        return {
            "status": "QPACK_ANALYSIS_COMPLETE",
            "verdict": verdict,
            "uncompressed_bytes": raw_total,
            "qpack_compressed_bytes": enc_total,
            "compression_savings_pct": round((1 - enc_total / raw_total) * 100, 1) if raw_total else 0,
            "summary": [
                ["HTTP status", " / ".join(str(s) for s in statuses)],
                ["Server QPACK_MAX_TABLE_CAPACITY", settings.get(0x1, 0)],
                ["Server QPACK_BLOCKED_STREAMS", settings.get(0x7, 0)],
                ["Our advertised table capacity", p.h3._max_table_capacity],
                ["Server encoder-stream bytes (dynamic inserts)", dyn_bytes],
                ["Our encoder-stream bytes", p.h3._encoder_bytes_sent],
                ["Total raw ➔ encoded", f"{raw_total} B ➔ {enc_total} B"],
            ],
            "table": {"columns": ["Request", "Direction", "Headers", "Raw bytes", "Encoded bytes",
                                  "Saved", "Encoder-stream bytes"], "rows": rows},
        }


# --------------------------------------------------------------------------
# 3. Congestion control
# --------------------------------------------------------------------------
@lab_test("RFC 9002 — QUIC Loss Detection and Congestion Control",
          "Uploads a real HTTP/3 POST body and samples aioquic's own congestion controller every 100 ms: "
          "congestion window, bytes in flight, smoothed RTT and packets declared lost. aioquic implements "
          "Reno and CUBIC; BBR is not available in this engine.",
          "Handshake ➔ POST upload ➔ sample cwnd / in-flight / RTT ➔ loss events from qlog")
async def congestion_benchmark(host: str, port: int, algorithm: str = "cubic",
                               upload_bytes: int = 4_000_000, duration: float = 4.0,
                               path: str = "/") -> Dict[str, Any]:
    requested = (algorithm or "cubic").lower()
    used = requested if requested in ("reno", "cubic") else "cubic"

    def configure(c):
        c.congestion_control_algorithm = used

    async with lab_session(host, port, configure=configure) as p:
        loss = p._quic._loss
        body = os.urandom(1024) * (upload_bytes // 1024)
        hdrs = _req_headers("POST", host, path, [(b"content-length", str(len(body)).encode())])
        start_sent, t0 = p.bytes_sent, time.perf_counter()
        sid, fut = p.request(hdrs, body=body)
        samples, prev_sent, prev_t, prev_lost = [], start_sent, t0, 0
        while time.perf_counter() - t0 < duration:
            await asyncio.sleep(0.1)
            now = time.perf_counter()
            lost = len(p.events("recovery:packet_lost"))
            mbps = (p.bytes_sent - prev_sent) * 8 / max(now - prev_t, 1e-6) / 1e6
            samples.append([round((now - t0) * 1000), round(loss.congestion_window / 1200, 1),
                            _kb(loss.bytes_in_flight), round(loss._rtt_smoothed * 1000, 1),
                            round(mbps, 2), lost - prev_lost])
            prev_sent, prev_t, prev_lost = p.bytes_sent, now, lost
            if fut.done() and loss.bytes_in_flight == 0:
                break
        elapsed = time.perf_counter() - t0
        sent = p.bytes_sent - start_sent
        status = _status_of(fut.result()) if fut.done() and not fut.exception() else None
        lost_total = len(p.events("recovery:packet_lost"))
        stopped = any(True for _ in p.frames("received", "stop_sending"))
        peak = max((s[1] for s in samples), default=0)
        peak_in_flight = max((e["data"].get("bytes_in_flight", 0)
                              for e in p.events("recovery:metrics_updated")), default=0)
        # If in-flight never came close to cwnd, the sender (Python/aioquic or the
        # uplink) was the bottleneck, not congestion control.
        app_limited = peak_in_flight < 0.5 * peak * 1200
        note = "" if used == requested else f" ({algorithm} not available in aioquic — ran {used})"
        verdict = (f"{used.upper()}{note}: sent {_mb(sent)} in {elapsed:.1f}s "
                   f"(avg {sent * 8 / elapsed / 1e6:.1f} Mbps), peak cwnd {peak} pkts, "
                   f"{lost_total} packets lost")
        if app_limited:
            verdict += " — application-limited: in-flight data never filled the window"
        if stopped:
            verdict += "; server sent STOP_SENDING (refused the upload body)"
        return {
            "status": "CONGESTION_BENCHMARK_COMPLETE",
            "verdict": verdict,
            "algorithm": used,
            "peak_cwnd_packets": peak,
            "summary": [
                ["Algorithm requested / used", f"{algorithm} / {used}"],
                ["Bytes sent on wire", _mb(sent)],
                ["Average send rate", f"{sent * 8 / elapsed / 1e6:.2f} Mbps"],
                ["Peak congestion window", f"{peak} packets"],
                ["Final smoothed RTT", f"{loss._rtt_smoothed * 1000:.1f} ms"],
                ["Min RTT", f"{loss._rtt_min * 1000:.1f} ms" if loss._rtt_min != float('inf') else "n/a"],
                ["Packets declared lost", lost_total],
                ["Peak bytes in flight", _kb(peak_in_flight)],
                ["Bottleneck", "sender / uplink (window never filled)" if app_limited
                 else "congestion window"],
                ["Server response", status or ("STOP_SENDING" if stopped else "none before end of test")],
            ],
            "table": {"columns": ["t (ms)", "cwnd (pkts)", "In flight", "sRTT (ms)", "Send rate (Mbps)",
                                  "Losses"], "rows": samples},
        }


# --------------------------------------------------------------------------
# 4. Path MTU (via Version Negotiation) & ECN
# --------------------------------------------------------------------------
def _set_dont_fragment(sock: socket.socket) -> bool:
    try:
        if sys.platform == "win32":
            sock.setsockopt(socket.IPPROTO_IP, 14, 1)          # IP_DONTFRAGMENT
        else:
            sock.setsockopt(socket.IPPROTO_IP, 10, 2)          # IP_MTU_DISCOVER = IP_PMTUDISC_DO
        return True
    except OSError:
        return False


@lab_test("RFC 9000 §14 & RFC 8899 — Datagram Packetization Layer PMTU Discovery",
          "Sends Don't-Fragment UDP datagrams of increasing size, each a QUIC packet with a reserved "
          "version. A QUIC server must answer every one it receives with Version Negotiation, so a reply "
          "proves a datagram of that size crossed the whole path unfragmented. ECN cannot be measured: "
          "Python cannot read the IP ECN bits of received packets on this platform.",
          "For each size: DF datagram ➔ Version Negotiation reply? ➔ largest size answered = path limit")
async def pmtud_probe(host: str, port: int) -> Dict[str, Any]:
    from app.protocols.quic_advanced import _parse_version_negotiation
    ip = _resolve_v4(host)
    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    df = _set_dont_fragment(sock)
    rows, largest = [], None
    try:
        for size in (1200, 1252, 1280, 1350, 1400, 1440, 1452, 1472, 1480, 1500):
            status, rtt = "NO_REPLY", None
            for _attempt in range(2):
                dcid, scid = os.urandom(8), os.urandom(8)
                pkt = bytes([0xC0]) + bytes.fromhex("1a2a3a4a") + bytes([8]) + dcid + bytes([8]) + scid
                pkt += b"\x00" * (size - len(pkt))
                t0 = time.perf_counter()
                try:
                    await loop.sock_sendto(sock, pkt, (ip, port))
                except OSError as e:
                    status = f"LOCAL_MTU_EXCEEDED (send refused by this machine, OS error {e.errno})"
                    break
                try:
                    while True:
                        data, _ = await asyncio.wait_for(loop.sock_recvfrom(sock, 4096), 1.0)
                        if _parse_version_negotiation(data, dcid, scid)["valid"]:
                            status, rtt = "REPLY", round((time.perf_counter() - t0) * 1000, 2)
                            break
                except asyncio.TimeoutError:
                    pass
                if status == "REPLY":
                    break
            if status == "REPLY":
                largest = size
            rows.append([size, size + 28, status, rtt if rtt is not None else "—"])
            if status.startswith("LOCAL_MTU_EXCEEDED"):
                break
    finally:
        sock.close()

    local_limit = any(r[2].startswith("LOCAL_MTU_EXCEEDED") for r in rows)
    if largest is None:
        verdict = "No size got a reply — server does not answer QUIC on this port, or UDP is blocked"
    else:
        verdict = (f"Largest datagram that crossed the path: {largest} B UDP payload "
                   f"(= {largest + 28} B IPv4 packet)")
        if local_limit:
            verdict += "; the next size was refused by this machine's own interface MTU"
        if not df:
            verdict += " — WARNING: could not set Don't-Fragment, so routers may have fragmented"
    return {
        "status": "PMTUD_PROBE_COMPLETE",
        "verdict": verdict,
        "discovered_path_mtu_bytes": largest,
        "ecn_validation": {"ip_ecn_marking": "NOT_MEASURABLE (no ECN socket access in Python)"},
        "summary": [
            ["Target IP", ip],
            ["Don't-Fragment bit set", "yes" if df else "no"],
            ["Largest UDP payload answered", f"{largest} B" if largest else "none"],
            ["Implied IP-level path MTU ≥", f"{largest + 28} B" if largest else "unknown"],
            ["QUIC minimum (RFC 9000)", "1200 B UDP payload"],
            ["ECN", "NOT_SUPPORTED — Python cannot read received ECN codepoints here"],
        ],
        "table": {"columns": ["UDP payload", "IP packet", "Result", "RTT (ms)"], "rows": rows},
    }


# --------------------------------------------------------------------------
# 5. Spin bit & connection-ID privacy
# --------------------------------------------------------------------------
@lab_test("RFC 9000 §17.4 (Latency Spin Bit) & §5.1 (Connection IDs)",
          "Real connection: 15 sequential PINGs while aioquic logs the spin bit of every new 1-RTT packet "
          "from the server. A server that spins flips the bit once per round trip (observers can measure "
          "RTT); a constant bit means spinning is disabled. Then switches to a fresh server-issued "
          "connection ID and checks the connection still works.",
          "Handshake ➔ PINGs (observe spin bit) ➔ NEW_CONNECTION_ID inventory ➔ rotate CID ➔ PING")
async def spinbit_cid_audit(host: str, port: int) -> Dict[str, Any]:
    async with lab_session(host, port, h3=False) as p:
        for _ in range(15):
            await p.timed_ping()
        states = [e["data"]["state"] for e in p.events("connectivity:spin_bit_updated")]
        flips = sum(1 for a, b in zip(states, states[1:]) if a != b)
        q = p._quic
        cids = [(q._peer_cid.sequence_number, q._peer_cid.cid.hex(), "in use")] + [
            (c.sequence_number, c.cid.hex(), "available") for c in q._peer_cid_available]
        old_cid = q._peer_cid.cid.hex()
        rotated, ping_after = False, None
        if q._peer_cid_available:
            p.change_connection_id()
            ping_after = await p.timed_ping()
            rotated = q._peer_cid.cid.hex() != old_cid
        spinning = flips >= 2
        verdict = (f"Spin bit {'ACTIVE' if spinning else 'DISABLED'} ({flips} flips over {len(states)} packets"
                   f"{' — on-path observers can measure RTT' if spinning else ''}); "
                   f"server issued {len(cids)} connection IDs; "
                   + (f"rotation to a new CID worked (PING {ping_after} ms)" if rotated
                      else "no spare CID to rotate to" if not q._peer_cid_available
                      else "rotation failed"))
        return {
            "status": "PRIVACY_AUDIT_COMPLETE",
            "verdict": verdict,
            "spin_bit_analysis": {"spin_bit_enabled": spinning, "flips": flips,
                                  "bit_sequence": [int(s) for s in states]},
            "cid_rotation_analysis": {"cids_issued": len(cids), "rotated": rotated},
            "summary": [
                ["Spin bit sequence (server)", "".join("1" if s else "0" for s in states) or "none"],
                ["Spin bit flips", flips],
                ["Connection IDs issued by server", len(cids)],
                ["CID before rotation", old_cid],
                ["CID after rotation", q._peer_cid.cid.hex()],
                ["Connection alive after rotation", "yes" if rotated else "n/a"],
            ],
            "table": {"columns": ["Sequence #", "Server connection ID", "State"],
                      "rows": [list(c) for c in cids]},
        }


# --------------------------------------------------------------------------
# 6. Connection migration
# --------------------------------------------------------------------------
@lab_test("RFC 9000 §9 — Connection Migration & Path Validation",
          "Real migration: after the handshake the client moves the live connection to a brand-new UDP "
          "socket (new local port, like a NAT rebinding or Wi-Fi ➔ cellular switch), rotating to a fresh "
          "connection ID first. The server must validate the new path (PATH_CHALLENGE / PATH_RESPONSE) and "
          "keep the connection alive.",
          "Handshake ➔ PING on old path ➔ rebind to new socket ➔ PATH_CHALLENGE/RESPONSE ➔ PING on new path")
async def connection_migration(host: str, port: int) -> Dict[str, Any]:
    new_transport = None
    try:
        async with lab_session(host, port, h3=False) as p:
            rtt_before = await p.timed_ping()
            old_local = p._transport.get_extra_info("sockname")
            disable = p.remote_params().get("disable_active_migration", False)
            rotated = False
            if p._quic._peer_cid_available:
                p.change_connection_id()
                rotated = True
            mark = len(p.events())
            sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
            sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
            sock.bind(("::", 0, 0, 0))
            new_transport, _ = await asyncio.get_running_loop().create_datagram_endpoint(
                lambda: p, sock=sock)               # connection_made() switches p._transport
            new_local = new_transport.get_extra_info("sockname")
            alive, rtt_after, err = True, None, ""
            try:
                rtt_after = await p.timed_ping(timeout=5.0)
            except asyncio.TimeoutError:
                alive, err = False, "no response on the new path within 5 s"
            except Exception as e:  # noqa: BLE001
                alive, err = False, f"{type(e).__name__}: {e}"
            after = p.events()[mark:]

            def count(direction, ftype):
                return sum(1 for e in after if e["name"] == f"transport:packet_{direction}"
                           for f in e["data"].get("frames", []) if f.get("frame_type") == ftype)
            challenges_in = count("received", "path_challenge")
            responses_out = count("sent", "path_response")
    finally:
        if new_transport is not None:
            new_transport.close()

    if alive:
        verdict = (f"Migration SUCCEEDED: local port {old_local[1]} ➔ {new_local[1]}; "
                   f"PING {rtt_before} ms ➔ {rtt_after} ms on the new path")
        verdict += (f"; server validated the path ({challenges_in} PATH_CHALLENGE)" if challenges_in
                    else "; server did not send PATH_CHALLENGE (accepted without validation)")
    elif disable:
        verdict = ("Migration REFUSED, as the server announced: it sets disable_active_migration, and "
                   f"after the client moved to port {new_local[1]} there was {err}")
    else:
        verdict = f"Migration FAILED although the server allows it: {err}"
    if alive and disable:
        verdict += " (despite the server setting disable_active_migration)"
    status = ("CONNECTION_MIGRATION_TEST_COMPLETE" if alive
              else "MIGRATION_DISABLED_BY_SERVER" if disable else "CONNECTION_MIGRATION_FAILED")
    return {
        "status": status,
        "verdict": verdict,
        "previous_path": f"[{old_local[0]}]:{old_local[1]}",
        "new_path": f"[{new_local[0]}]:{new_local[1]}",
        "summary": [
            ["Old local socket", f"[{old_local[0]}]:{old_local[1]}"],
            ["New local socket", f"[{new_local[0]}]:{new_local[1]}"],
            ["Server disable_active_migration", bool(disable)],
            ["Rotated connection ID before migrating", rotated],
            ["PATH_CHALLENGE frames from server", challenges_in],
            ["PATH_RESPONSE frames we sent", responses_out],
            ["PING RTT before / after", f"{rtt_before} ms / {rtt_after if rtt_after is not None else '—'} ms"],
            ["Connection alive after migration", "yes" if alive else "no"],
        ],
        "table": None,
    }


# --------------------------------------------------------------------------
# 7. DATAGRAM extension
# --------------------------------------------------------------------------
@lab_test("RFC 9221 — An Unreliable Datagram Extension to QUIC",
          "Advertises max_datagram_frame_size and reads the server's value from its real transport "
          "parameters. If supported, sends 20 DATAGRAM frames and checks the server's ACK frames to see "
          "which packets carrying them arrived (DATAGRAM frames are ACKed but never retransmitted).",
          "Handshake (max_datagram_frame_size) ➔ 20 × DATAGRAM ➔ PING ➔ match ACK ranges")
async def datagram_extension(host: str, port: int, count: int = 20) -> Dict[str, Any]:
    def configure(c):
        c.max_datagram_frame_size = 65536

    async with lab_session(host, port, configure=configure, h3=False) as p:
        mx = p.remote_params().get("max_datagram_frame_size")
        if not mx:
            return {"status": "DATAGRAM_NOT_SUPPORTED",
                    "verdict": "Server does not support the DATAGRAM extension (no max_datagram_frame_size)",
                    "datagrams_sent": 0, "datagrams_received": 0, "loss_rate_pct": None,
                    "summary": [["Server max_datagram_frame_size", "not advertised"]], "table": None}
        size = min(200, mx - 8)
        for i in range(count):
            p._quic.send_datagram_frame(i.to_bytes(4, "big") + os.urandom(size - 4))
            p.transmit()
            await asyncio.sleep(0.01)
        try:
            await p.timed_ping()
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(0.3)
        dg_pns = {e["data"]["header"]["packet_number"] for e, _ in p.frames("sent", "datagram")}
        acked = set()
        for _, f in p.frames("received", "ack"):
            for lo, hi in f.get("acked_ranges", []):
                acked.update(pn for pn in dg_pns if lo <= pn <= hi)
        sent_frames = sum(1 for _ in p.frames("sent", "datagram"))
        closed = p.terminated is not None
    loss_pct = round((1 - len(acked) / len(dg_pns)) * 100, 1) if dg_pns else None
    return {
        "status": "DATAGRAM_EXTENSION_TEST_COMPLETE",
        "verdict": (f"Server supports DATAGRAM (max frame {mx} B); {len(acked)}/{len(dg_pns)} packets "
                    f"carrying {sent_frames} datagrams were ACKed ({loss_pct}% lost)"
                    + (" — server then closed the connection" if closed else "")),
        "datagrams_sent": sent_frames,
        "datagrams_received": len(acked),
        "loss_rate_pct": loss_pct,
        "summary": [
            ["Server max_datagram_frame_size", f"{mx} B"],
            ["Datagram payload size", f"{size} B"],
            ["DATAGRAM frames sent", sent_frames],
            ["Packets carrying them / ACKed", f"{len(dg_pns)} / {len(acked)}"],
            ["Loss", f"{loss_pct}%"],
            ["Connection closed by server", "yes" if closed else "no"],
        ],
        "table": None,
    }


# --------------------------------------------------------------------------
# 8. ECH
# --------------------------------------------------------------------------
_HPKE_KEM = {0x0010: "DHKEM(P-256, HKDF-SHA256)", 0x0011: "DHKEM(P-384, HKDF-SHA384)",
             0x0012: "DHKEM(P-521, HKDF-SHA512)", 0x0020: "DHKEM(X25519, HKDF-SHA256)",
             0x0021: "DHKEM(X448, HKDF-SHA512)"}
_HPKE_KDF = {0x0001: "HKDF-SHA256", 0x0002: "HKDF-SHA384", 0x0003: "HKDF-SHA512"}
_HPKE_AEAD = {0x0001: "AES-128-GCM", 0x0002: "AES-256-GCM", 0x0003: "ChaCha20-Poly1305"}


def _parse_ech_config_list(data: bytes) -> List[Dict[str, Any]]:
    """Parse an ECHConfigList (draft-ietf-tls-esni §4)."""
    out, i = [], 2                                   # skip 2-byte list length
    while i + 4 <= len(data):
        version = int.from_bytes(data[i:i + 2], "big")
        length = int.from_bytes(data[i + 2:i + 4], "big")
        body = data[i + 4:i + 4 + length]
        i += 4 + length
        if version != 0xFE0D:
            out.append({"version": f"0x{version:04x}", "note": "unknown ECH version"})
            continue
        j = 0
        config_id = body[j]; j += 1
        kem = int.from_bytes(body[j:j + 2], "big"); j += 2
        pk_len = int.from_bytes(body[j:j + 2], "big"); j += 2 + pk_len
        cs_len = int.from_bytes(body[j:j + 2], "big"); j += 2
        suites = []
        for k in range(j, j + cs_len, 4):
            kdf = int.from_bytes(body[k:k + 2], "big")
            aead = int.from_bytes(body[k + 2:k + 4], "big")
            suites.append(f"{_HPKE_KDF.get(kdf, hex(kdf))} + {_HPKE_AEAD.get(aead, hex(aead))}")
        j += cs_len
        max_name = body[j]; j += 1
        name_len = body[j]; j += 1
        public_name = body[j:j + name_len].decode(errors="replace")
        out.append({"version": "0xfe0d", "config_id": config_id, "kem": _HPKE_KEM.get(kem, hex(kem)),
                    "public_key_bytes": pk_len, "cipher_suites": suites,
                    "maximum_name_length": max_name, "public_name": public_name})
    return out


@lab_test("RFC 9460 (HTTPS DNS records) & draft-ietf-tls-esni — Encrypted ClientHello",
          "Looks up the target's real DNS HTTPS record and parses any published ECHConfigList: the "
          "outer (public) SNI, HPKE KEM and cipher suites. This client (aioquic) cannot send ECH itself, "
          "so the SNI of QUICLAB's own connections remains visible on the wire.",
          "DNS HTTPS query ➔ SvcParams (alpn, ech) ➔ parse ECHConfigList")
async def ech_check(host: str, port: int) -> Dict[str, Any]:
    import dns.resolver
    from dns.rdtypes.svcbbase import ParamKey

    def lookup():
        try:
            return dns.resolver.resolve(host, "HTTPS", lifetime=5.0)
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return None

    t0 = time.perf_counter()
    answer = await asyncio.to_thread(lookup)
    dns_ms = round((time.perf_counter() - t0) * 1000, 2)
    if not answer:
        return {"status": "NO_HTTPS_RECORD",
                "verdict": f"{host} publishes no DNS HTTPS record, so no ECH config is available",
                "summary": [["DNS lookup time", f"{dns_ms} ms"]], "table": None}
    alpns, configs = [], []
    for rr in answer:
        params = rr.params
        if ParamKey.ALPN in params:
            alpns += [a.decode() for a in params[ParamKey.ALPN].ids]
        if ParamKey.ECH in params:
            configs += _parse_ech_config_list(params[ParamKey.ECH].ech)
    if not configs:
        return {"status": "ECH_NOT_PUBLISHED",
                "verdict": f"HTTPS record found (alpn: {', '.join(alpns) or 'none'}) but no ECH config — "
                           "SNI is sent in clear",
                "summary": [["Advertised ALPN", ", ".join(alpns) or "none"],
                            ["DNS lookup time", f"{dns_ms} ms"]],
                "table": None}
    c0 = configs[0]
    return {
        "status": "ECH_PUBLISHED",
        "verdict": (f"ECH is published: outer SNI '{c0.get('public_name')}' hides inner SNI '{host}' "
                    f"({c0.get('kem')}). QUICLAB itself cannot send ECH (aioquic lacks it)."),
        "outer_sni_host": c0.get("public_name"),
        "inner_sni_host": host,
        "ech_hpke_cipher": f"{c0.get('kem')}, {', '.join(c0.get('cipher_suites', []))}",
        "summary": [
            ["Advertised ALPN", ", ".join(alpns) or "none"],
            ["ECH configs published", len(configs)],
            ["Outer (public) SNI", c0.get("public_name")],
            ["Inner (protected) SNI", host],
            ["DNS lookup time", f"{dns_ms} ms"],
        ],
        "table": {"columns": ["Config ID", "Version", "KEM", "Cipher suites", "Public name", "Max name len"],
                  "rows": [[c.get("config_id"), c.get("version"), c.get("kem"),
                            ", ".join(c.get("cipher_suites", [])), c.get("public_name"),
                            c.get("maximum_name_length")] for c in configs]},
    }


# --------------------------------------------------------------------------
# 9. Flow control
# --------------------------------------------------------------------------
@lab_test("RFC 9000 §4 — Flow Control",
          "Reads the flow-control limits the server really advertised in its transport parameters, then "
          "downloads a page over HTTP/3 and counts MAX_DATA / MAX_STREAM_DATA / *_BLOCKED frames in both "
          "directions. The upload ceiling is window ÷ RTT: a sender can never exceed it.",
          "Handshake (transport params) ➔ GET ➔ count window updates ➔ window/RTT ceiling")
async def flow_control(host: str, port: int, path: str = "/") -> Dict[str, Any]:
    async with lab_session(host, port) as p:
        rp = p.remote_params()
        local = p._quic._configuration
        t0 = time.perf_counter()
        _, fut = p.request(_req_headers("GET", host, path))
        evs = await asyncio.wait_for(fut, DEFAULT_TIMEOUT * 2)
        dl_s = time.perf_counter() - t0
        body = sum(len(e.data) for e in evs if isinstance(e, DataReceived))
        srtt = p._quic._loss._rtt_smoothed
        counts = {f"{d}:{t}": sum(1 for _ in p.frames(d, t))
                  for d in ("sent", "received")
                  for t in ("max_data", "max_stream_data", "data_blocked", "stream_data_blocked")}
    conn_win = rp.get("initial_max_data")
    stream_win = rp.get("initial_max_stream_data_bidi_remote")
    limit = min(x for x in (conn_win, stream_win) if x) if (conn_win or stream_win) else None
    ceiling = limit * 8 / srtt / 1e6 if limit and srtt else None
    rows = [
        ["initial_max_data (connection)", _mb(conn_win), _mb(local.max_data)],
        ["initial_max_stream_data_bidi_local", _mb(rp.get("initial_max_stream_data_bidi_local")), _mb(local.max_stream_data)],
        ["initial_max_stream_data_bidi_remote", _mb(stream_win), _mb(local.max_stream_data)],
        ["initial_max_stream_data_uni", _mb(rp.get("initial_max_stream_data_uni")), _mb(local.max_stream_data)],
        ["initial_max_streams_bidi", rp.get("initial_max_streams_bidi"), 128],
        ["initial_max_streams_uni", rp.get("initial_max_streams_uni"), 128],
    ]
    return {
        "status": "FLOW_CONTROL_TEST_COMPLETE",
        "verdict": (f"Server allows {_mb(conn_win)} per connection / {_mb(stream_win)} per stream; "
                    f"at {srtt * 1000:.1f} ms RTT a client upload is capped at "
                    + (f"{ceiling:.0f} Mbps until the server sends MAX_DATA" if ceiling else "n/a")),
        "connection_max_data_bytes": conn_win,
        "stream_max_data_bytes": stream_win,
        "summary": [
            ["Smoothed RTT", f"{srtt * 1000:.1f} ms"],
            ["Window ÷ RTT upload ceiling", f"{ceiling:.0f} Mbps" if ceiling else "n/a"],
            ["Downloaded body", f"{_kb(body)} in {dl_s * 1000:.0f} ms"],
            ["MAX_DATA / MAX_STREAM_DATA we sent", f"{counts['sent:max_data']} / {counts['sent:max_stream_data']}"],
            ["MAX_DATA / MAX_STREAM_DATA received", f"{counts['received:max_data']} / {counts['received:max_stream_data']}"],
            ["*_BLOCKED frames sent / received",
             f"{counts['sent:data_blocked'] + counts['sent:stream_data_blocked']} / "
             f"{counts['received:data_blocked'] + counts['received:stream_data_blocked']}"],
        ],
        "table": {"columns": ["Transport parameter", "Server", "QUICLAB client"], "rows": rows},
    }


# --------------------------------------------------------------------------
# 10. ACK behaviour
# --------------------------------------------------------------------------
@lab_test("RFC 9000 §13.2 (ACK generation) & draft-ietf-quic-ack-frequency",
          "Uploads data for ~2 s and measures how the server actually acknowledges it: ack-eliciting "
          "packets we sent vs ACK frames received, and the ack_delay values the server reported. The "
          "ACK_FREQUENCY extension itself cannot be negotiated — aioquic does not implement it.",
          "Handshake (max_ack_delay) ➔ POST upload ➔ count ACK frames & ack_delay ➔ packets per ACK")
async def ack_behaviour(host: str, port: int, path: str = "/") -> Dict[str, Any]:
    async with lab_session(host, port) as p:
        rp = p.remote_params()
        mark = len(p.events())
        body = os.urandom(1024) * 1500
        _, fut = p.request(_req_headers("POST", host, path,
                                        [(b"content-length", str(len(body)).encode())]), body=body)
        t0 = time.perf_counter()
        while time.perf_counter() - t0 < 2.0 and not (fut.done() and p._quic._loss.bytes_in_flight == 0):
            await asyncio.sleep(0.05)
        after = p.events()[mark:]
    eliciting = sum(1 for e in after if e["name"] == "transport:packet_sent"
                    and any(f.get("frame_type") not in ("ack", "padding") for f in e["data"].get("frames", [])))
    delays = [f.get("ack_delay", 0) for e in after if e["name"] == "transport:packet_received"
              for f in e["data"].get("frames", []) if f.get("frame_type") == "ack"]
    acks = len(delays)
    ratio = round(eliciting / acks, 2) if acks else None
    max_ack_delay = rp.get("max_ack_delay", 25)
    return {
        "status": "ACK_FREQUENCY_TEST_COMPLETE",
        "verdict": (f"Server sent {acks} ACKs for {eliciting} ack-eliciting packets "
                    f"(1 ACK per {ratio} packets); reported ack_delay avg "
                    f"{(sum(delays) / acks) if acks else 0:.2f} ms, max {max(delays, default=0):.2f} ms "
                    f"(advertised max_ack_delay {max_ack_delay} ms)"),
        "max_ack_delay_ms": max_ack_delay,
        "ack_eliciting_threshold": ratio,
        "summary": [
            ["Server max_ack_delay", f"{max_ack_delay} ms"],
            ["Server ack_delay_exponent", rp.get("ack_delay_exponent", 3)],
            ["Ack-eliciting packets sent", eliciting],
            ["ACK frames received", acks],
            ["Packets per ACK (observed)", ratio],
            ["Average / max reported ack_delay",
             f"{(sum(delays) / acks) if acks else 0:.2f} / {max(delays, default=0):.2f} ms"],
            ["ACK_FREQUENCY extension", "NOT_SUPPORTED by aioquic (cannot negotiate)"],
        ],
        "table": None,
    }


# --------------------------------------------------------------------------
# 11. Stateless reset
# --------------------------------------------------------------------------
@lab_test("RFC 9000 §10.3 — Stateless Reset",
          "Opens a real connection and records a server-issued connection ID together with its stateless "
          "reset token. After closing the connection, sends packets to that dead connection ID. A server "
          "that supports stateless reset answers with a packet whose last 16 bytes equal the token it "
          "issued earlier — which this test verifies byte-for-byte.",
          "Handshake ➔ NEW_CONNECTION_ID (token) ➔ close ➔ packet to dead CID ➔ compare last 16 bytes")
async def stateless_reset(host: str, port: int) -> Dict[str, Any]:
    async with lab_session(host, port, h3=False) as p:
        await p.timed_ping()
        await asyncio.sleep(0.3)
        q = p._quic
        candidates = [c for c in q._peer_cid_available if c.stateless_reset_token]
        pick = candidates[-1] if candidates else q._peer_cid
        cid, token = pick.cid, pick.stateless_reset_token
        # The socket is unconnected (no peername); reuse the exact address tuple
        # aioquic sent to (IPv6 or IPv4-mapped) from the same kind of socket.
        peer_addr = p._quic._network_paths[0].addr
    if not token:
        return {"status": "NO_RESET_TOKEN",
                "verdict": ("Server provided no stateless reset token (no stateless_reset_token transport "
                            "parameter and no spare connection IDs), so it cannot stateless-reset this connection"),
                "reset_token_hex": None, "connection_termination_action": "NONE",
                "summary": [["Connection IDs issued", 1 + len(candidates)]], "table": None}

    loop = asyncio.get_running_loop()
    sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
    sock.bind(("::", 0, 0, 0))
    sock.setblocking(False)
    rows, verified = [], False
    try:
        for wait in (0.5, 1.0, 1.5, 2.0):
            await asyncio.sleep(wait)
            pkt = bytes([0x40 | (os.urandom(1)[0] & 0x3F)]) + cid + os.urandom(1200 - 1 - len(cid))
            await loop.sock_sendto(sock, pkt, peer_addr)
            try:
                data, _ = await asyncio.wait_for(loop.sock_recvfrom(sock, 4096), 1.5)
            except asyncio.TimeoutError:
                rows.append([len(rows) + 1, "no reply", "—", "—"])
                continue
            match = data[-16:] == token
            rows.append([len(rows) + 1, f"{len(data)} B", data[-16:].hex(), "MATCH" if match else "different"])
            if match:
                verified = True
                break
    finally:
        sock.close()
    verdict = ("Stateless reset VERIFIED: the server's reply ended with the exact token it issued"
               if verified else
               "No valid stateless reset received (server may not implement it, or routes the dead CID elsewhere)")
    return {
        "status": "STATELESS_RESET_VERIFIED" if verified else "STATELESS_RESET_NOT_OBSERVED",
        "verdict": verdict,
        "reset_token_hex": token.hex(),
        "connection_termination_action": "RESET_RECEIVED" if verified else "NONE",
        "summary": [
            ["Dead connection ID probed", cid.hex()],
            ["CID sequence number", pick.sequence_number],
            ["Expected reset token", token.hex()],
            ["Result", "token matched" if verified else "not observed"],
        ],
        "table": {"columns": ["Attempt", "Reply", "Last 16 bytes", "vs token"], "rows": rows},
    }


# --------------------------------------------------------------------------
# 13. CRYPTO reassembly
# --------------------------------------------------------------------------
@lab_test("RFC 9000 §19.6 — CRYPTO Frames & Reassembly",
          "Pads the TLS ClientHello (extra ALPN entries the server ignores) so it spans two Initial "
          "packets, then sends those packets in REVERSE order. The server receives the CRYPTO frame at a "
          "non-zero offset first and must buffer it until offset 0 arrives. A completed handshake proves "
          "real out-of-order reassembly.",
          "Big ClientHello ➔ Initial #2 (offset > 0) sent first ➔ Initial #1 (offset 0) ➔ handshake?")
async def crypto_reassembly(host: str, port: int) -> Dict[str, Any]:
    alpn = list(H3_ALPN) + [f"quiclab-pad-{i:03d}" for i in range(90)]

    def before(p):
        p.reverse_first_flight = True

    async with lab_session(host, port, alpn=alpn, h3=False, before_connect=before) as p:
        crypto = [(e["data"]["header"]["packet_number"], f["offset"], f["length"])
                  for e, f in p.frames("sent", "crypto")
                  if e["data"]["header"].get("packet_type") == "initial"][:len(p.first_flight_sizes) or None]
        sizes, hs_ms = p.first_flight_sizes, p.handshake_ms
        alpn_chosen = p._quic.tls.alpn_negotiated
    reordered = len(sizes) > 1
    order = " ➔ ".join(f"offset {o}" for _, o, _ in sorted(crypto, key=lambda c: -c[1])) if reordered else "single packet"
    return {
        "status": "CRYPTO_REASSEMBLY_TEST_COMPLETE",
        "verdict": (f"Server reassembled a ClientHello split over {len(sizes)} Initial packets delivered out "
                    f"of order; handshake completed in {hs_ms} ms" if reordered else
                    "ClientHello fit in one packet, so it could not be reordered (handshake still completed)"),
        "flight_arrival_order": order,
        "reassembly_buffer_state": "REASSEMBLED" if reordered else "NOT_EXERCISED",
        "summary": [
            ["First-flight datagrams", len(sizes)],
            ["Order sent", order],
            ["Handshake time", f"{hs_ms} ms"],
            ["ALPN chosen by server", alpn_chosen],
        ],
        "table": {"columns": ["Packet #", "CRYPTO offset", "CRYPTO length"],
                  "rows": [list(c) for c in crypto]},
    }


# --------------------------------------------------------------------------
# 14. Multipath
# --------------------------------------------------------------------------
@lab_test("draft-ietf-quic-multipath — Multipath Extension for QUIC",
          "Multipath QUIC needs the enable_multipath transport parameter and PATH_ACK / PATH_STATUS frames, "
          "which aioquic does not implement. Nothing is sent; this lists this machine's network interfaces "
          "that a multipath-capable client could use as separate paths.")
async def multipath(host: str, port: int) -> Dict[str, Any]:
    import psutil
    rows = []
    stats = psutil.net_if_stats()
    for name, addrs in psutil.net_if_addrs().items():
        st = stats.get(name)
        if not st or not st.isup:
            continue
        for a in addrs:
            if a.family == socket.AF_INET and not a.address.startswith("127."):
                rows.append([name, a.address, f"{st.speed} Mbps" if st.speed else "unknown"])
    return {
        "status": "MULTIPATH_NOT_SUPPORTED",
        "verdict": (f"Not testable: aioquic has no multipath support. {len(rows)} usable IPv4 interface(s) "
                    "found that could serve as paths."),
        "packet_scheduler_policy": "N/A",
        "aggregate_throughput": "N/A",
        "summary": [["Multipath support in engine", "NOT_SUPPORTED (aioquic)"],
                    ["Candidate local paths", len(rows)]],
        "table": {"columns": ["Interface", "IPv4 address", "Link speed"], "rows": rows},
    }


# --------------------------------------------------------------------------
# 15. WebTransport
# --------------------------------------------------------------------------
_H3_SETTING_NAMES = {0x1: "QPACK_MAX_TABLE_CAPACITY", 0x6: "MAX_FIELD_SECTION_SIZE",
                     0x7: "QPACK_BLOCKED_STREAMS", 0x8: "ENABLE_CONNECT_PROTOCOL", 0x33: "H3_DATAGRAM",
                     0x2B603742: "ENABLE_WEBTRANSPORT (draft-02)", 0xC671706A: "WEBTRANSPORT_MAX_SESSIONS",
                     0x2B603743: "WEBTRANSPORT_MAX_SESSIONS (old)"}


@lab_test("RFC 9220 (Extended CONNECT for H3) & draft-ietf-webtrans-http3 — WebTransport over HTTP/3",
          "Opens a real HTTP/3 connection advertising WebTransport, reads the server's SETTINGS, and — if "
          "the server enables Extended CONNECT — sends CONNECT with :protocol=webtransport to the path "
          "and reports the server's real :status (200 = session established).",
          "Handshake ➔ SETTINGS ➔ Extended CONNECT (:protocol webtransport) ➔ :status")
async def webtransport(host: str, port: int, path: str = "/") -> Dict[str, Any]:
    def configure(c):
        c.max_datagram_frame_size = 65536

    async with lab_session(host, port, webtransport=True, configure=configure) as p:
        s = await _await_settings(p)
        connect_ok = s.get(0x8) == 1
        wt_enabled = s.get(0x2B603742) == 1 or bool(s.get(0xC671706A))
        status, sid = None, None
        if connect_ok:
            sid, fut = p.request(_req_headers("CONNECT", host, path, [
                (b":protocol", b"webtransport"), (b"sec-webtransport-http3-draft02", b"1"),
                (b"origin", f"https://{host}".encode())]), headers_only=True)
            try:
                status = _status_of(await asyncio.wait_for(fut, 5.0))
            except asyncio.TimeoutError:
                status = "no response"
    def _setting_name(k: int) -> str:
        if k in _H3_SETTING_NAMES:
            return _H3_SETTING_NAMES[k]
        if k >= 0x21 and (k - 0x21) % 0x1F == 0:          # RFC 9114 §7.2.4.1 reserved
            return f"0x{k:x} (reserved / GREASE)"
        return f"0x{k:x} (unknown)"

    rows = [[_setting_name(k), v] for k, v in sorted(s.items())]
    if not connect_ok:
        verdict = "Server does not enable Extended CONNECT — WebTransport is not available"
    elif status == "200":
        verdict = f"WebTransport session ESTABLISHED on {path} (stream {sid})"
    else:
        verdict = (f"Extended CONNECT allowed{' and WebTransport advertised' if wt_enabled else ''}, "
                   f"but CONNECT {path} returned {status}")
    return {
        "status": "WEBTRANSPORT_TEST_COMPLETE",
        "verdict": verdict,
        "session_id": sid,
        "summary": [
            ["ENABLE_CONNECT_PROTOCOL", "yes" if connect_ok else "no"],
            ["H3_DATAGRAM", "yes" if s.get(0x33) == 1 else "no"],
            ["WebTransport advertised", "yes" if wt_enabled else "no"],
            [f"CONNECT {path} :status", status or "not attempted"],
        ],
        "table": {"columns": ["Server SETTING", "Value"], "rows": rows},
    }
