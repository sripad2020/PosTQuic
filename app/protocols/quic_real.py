"""
Real QUIC + HTTP/3 engine backed by aioquic.

Unlike the raw-UDP probes elsewhere in the codebase, this module performs a
genuine RFC 9000 QUIC transport handshake with a real TLS 1.3 key exchange,
negotiates ALPN, and exposes the actual peer certificate chain, negotiated
QUIC version, cipher suite and handshake RTT. HTTP/3 requests are issued over
a real H3 connection (RFC 9114) and return the server's true status, headers
and body.

If aioquic is unavailable the AIOQUIC_AVAILABLE flag is False and callers can
fall back to a labelled raw-socket probe.
"""
import ssl
import time
import socket
import asyncio
from typing import Dict, Any, List, Optional, Tuple

try:
    from aioquic.asyncio.client import connect
    from aioquic.asyncio.protocol import QuicConnectionProtocol
    from aioquic.quic.configuration import QuicConfiguration
    from aioquic.quic.logger import QuicLogger
    from aioquic.quic.events import QuicEvent
    from aioquic.h3.connection import H3_ALPN, H3Connection
    from aioquic.h3.events import HeadersReceived, DataReceived, H3Event
    AIOQUIC_AVAILABLE = True

    class _QuietProtocol(QuicConnectionProtocol):
        """Ignores stream data. The default protocol creates asyncio stream
        writers for the server's HTTP/3 control streams, which then raise
        'Cannot send data on peer-initiated unidirectional stream' on GC."""
        def quic_event_received(self, event: QuicEvent) -> None:
            pass

    class _H3Client(QuicConnectionProtocol):
        """QuicConnectionProtocol that drives a single HTTP/3 request/response.

        Overriding quic_event_received is the supported way to bridge QUIC
        events into an H3Connection without racing the protocol's own loop.
        """
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._http = H3Connection(self._quic)
            self._request_events: Dict[int, List[H3Event]] = {}
            self._request_waiter: Dict[int, asyncio.Future] = {}

        def send_request(self, stream_id: int, h3_headers, body: bytes) -> asyncio.Future:
            self._http.send_headers(stream_id, h3_headers, end_stream=not body)
            if body:
                self._http.send_data(stream_id, body, end_stream=True)
            waiter = self._loop.create_future()
            self._request_events[stream_id] = []
            self._request_waiter[stream_id] = waiter
            self.transmit()
            return waiter

        def quic_event_received(self, event: QuicEvent) -> None:
            for h3_event in self._http.handle_event(event):
                sid = getattr(h3_event, "stream_id", None)
                if sid in self._request_events:
                    self._request_events[sid].append(h3_event)
                    if getattr(h3_event, "stream_ended", False):
                        waiter = self._request_waiter.pop(sid)
                        if not waiter.done():
                            waiter.set_result(self._request_events.pop(sid))
except Exception:  # pragma: no cover - only when aioquic missing
    AIOQUIC_AVAILABLE = False


def _cipher_suite_name(tls_ctx) -> Optional[str]:
    try:
        ks = getattr(tls_ctx, "key_schedule", None)
        if ks is not None and getattr(ks, "cipher_suite", None) is not None:
            return ks.cipher_suite.name
    except Exception:
        pass
    return None


def _cert_summary(cert) -> Dict[str, Any]:
    """Extract real fields from a cryptography x509.Certificate."""
    if cert is None:
        return {}
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import rsa, ec
    import datetime

    def _name(n) -> str:
        try:
            return n.rfc4514_string()
        except Exception:
            return str(n)

    sans: List[str] = []
    key_usage: List[str] = []
    eku: List[str] = []
    must_staple = False
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        sans = ext.value.get_values_for_type(x509.DNSName)
    except Exception:
        pass
    try:
        ku = cert.extensions.get_extension_for_class(x509.KeyUsage).value
        for flag in ("digital_signature", "content_commitment", "key_encipherment",
                     "data_encipherment", "key_agreement", "key_cert_sign", "crl_sign"):
            try:
                if getattr(ku, flag):
                    key_usage.append(flag)
            except ValueError:
                pass
    except Exception:
        pass
    try:
        for usage in cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value:
            eku.append(usage._name if hasattr(usage, "_name") else usage.dotted_string)
    except Exception:
        pass
    try:
        tls_feat = cert.extensions.get_extension_for_class(x509.TLSFeature).value
        must_staple = any(f == x509.TLSFeatureType.status_request for f in tls_feat)
    except Exception:
        pass

    pub = cert.public_key()
    if isinstance(pub, rsa.RSAPublicKey):
        key_type, key_bits = "RSA", pub.key_size
    elif isinstance(pub, ec.EllipticCurvePublicKey):
        key_type, key_bits = f"EC ({pub.curve.name})", pub.curve.key_size
    else:
        key_type, key_bits = type(pub).__name__, getattr(pub, "key_size", 0)

    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        not_after = cert.not_valid_after_utc
        not_before = cert.not_valid_before_utc
    except AttributeError:  # older cryptography
        not_after = cert.not_valid_after.replace(tzinfo=datetime.timezone.utc)
        not_before = cert.not_valid_before.replace(tzinfo=datetime.timezone.utc)

    days_remaining = (not_after - now).days

    cn = ""
    try:
        cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
    except Exception:
        pass
    issuer_org = ""
    try:
        issuer_org = cert.issuer.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)[0].value
    except Exception:
        try:
            issuer_org = cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value
        except Exception:
            pass

    return {
        "subject": _name(cert.subject),
        "subject_cn": cn,
        "issuer": _name(cert.issuer),
        "issuer_org": issuer_org,
        "serial_hex": format(cert.serial_number, "x"),
        "version": cert.version.name,
        "signature_algorithm": cert.signature_algorithm_oid._name,
        "signature_hash": getattr(cert.signature_hash_algorithm, "name", "unknown"),
        "public_key_type": key_type,
        "public_key_bits": key_bits,
        "not_before": not_before.isoformat(),
        "not_after": not_after.isoformat(),
        "days_remaining": days_remaining,
        "expired": now > not_after,
        "san": sans,
        "san_count": len(sans),
        "key_usage": key_usage,
        "extended_key_usage": eku,
        "ocsp_must_staple": must_staple,
    }


def _build_config(alpn: List[str], verify: bool, keylog_path: Optional[str] = None,
                  session_ticket=None, qlog: bool = False) -> "QuicConfiguration":
    config = QuicConfiguration(is_client=True, alpn_protocols=alpn)
    if verify:
        config.load_verify_locations(None)  # system trust store via certifi default
    else:
        config.verify_mode = ssl.CERT_NONE
    if qlog:
        config.quic_logger = QuicLogger()
    if session_ticket is not None:
        config.session_ticket = session_ticket
    if keylog_path:
        try:
            config.secrets_log_file = open(keylog_path, "a")
        except Exception:
            pass
    return config


async def perform_quic_handshake(
    host: str,
    port: int = 443,
    alpn: Optional[List[str]] = None,
    sni: Optional[str] = None,
    verify: bool = False,
    timeout: float = 8.0,
) -> Dict[str, Any]:
    """Perform a genuine QUIC+TLS 1.3 handshake and report real negotiated state."""
    alpn = alpn or list(H3_ALPN)
    sni = sni or host

    try:
        ip = socket.gethostbyname(host)
    except Exception as e:
        return {"success": False, "engine": "aioquic", "error": f"DNS resolution failed: {e}",
                "host": host, "port": port}

    config = _build_config(alpn, verify)
    config.server_name = sni

    t0 = time.perf_counter()
    try:
        async with connect(host, port, configuration=config, create_protocol=_QuietProtocol, wait_connected=False) as protocol:
            # connect(wait_connected=False) does not send the Initial by itself;
            # without this the handshake never starts and always times out.
            protocol.transmit()
            await asyncio.wait_for(protocol.wait_connected(), timeout=timeout)
            handshake_ms = round((time.perf_counter() - t0) * 1000.0, 2)

            quic = protocol._quic
            tls = quic.tls
            version = getattr(quic, "_version", None)
            peer_cert = getattr(tls, "_peer_certificate", None)
            chain = getattr(tls, "_peer_certificate_chain", []) or []

            # Measure an application-level RTT via a QUIC PING / idle probe.
            rtt_sample = None
            try:
                tp0 = time.perf_counter()
                await asyncio.wait_for(protocol.ping(), timeout=timeout)
                rtt_sample = round((time.perf_counter() - tp0) * 1000.0, 2)
            except Exception:
                rtt_sample = None

            result = {
                "success": True,
                "engine": "aioquic (real QUIC handshake)",
                "host": host,
                "port": port,
                "ip_address": ip,
                "sni": sni,
                "quic_version": f"0x{version:08x}" if isinstance(version, int) else str(version),
                "alpn_negotiated": getattr(tls, "alpn_negotiated", None),
                "tls_version": "TLS 1.3",
                "cipher_suite": _cipher_suite_name(tls),
                "early_data_accepted": bool(getattr(tls, "early_data_accepted", False)),
                "session_resumed": bool(getattr(tls, "_session_resumed", False)),
                "handshake_ms": handshake_ms,
                "ping_rtt_ms": rtt_sample,
                "peer_certificate": _cert_summary(peer_cert),
                "certificate_chain_depth": len(chain) + (1 if peer_cert else 0),
                "chain_issuers": [
                    (c.issuer.rfc4514_string() if c is not None else "") for c in chain
                ][:5],
            }
            return result
    except asyncio.TimeoutError:
        return {"success": False, "engine": "aioquic", "host": host, "port": port,
                "ip_address": ip,
                "error": f"QUIC handshake timed out after {timeout}s (target may not speak QUIC on udp/{port})"}
    except Exception as e:
        return {"success": False, "engine": "aioquic", "host": host, "port": port,
                "ip_address": ip, "error": f"QUIC handshake failed: {type(e).__name__}: {e}"}


async def _resume_with_ticket(host: str, port: int, alpn: List[str], sni: str,
                              verify: bool, ticket, timeout: float) -> Dict[str, Any]:
    """Reconnect using a stored session ticket. aioquic offers 0-RTT on its own
    whenever the ticket allows early data; we then read what the server decided."""
    config = _build_config(alpn, verify, session_ticket=ticket)
    config.server_name = sni
    t0 = time.perf_counter()
    try:
        async with connect(host, port, configuration=config, create_protocol=_QuietProtocol, wait_connected=False) as protocol:
            # connect(wait_connected=False) does not send the Initial by itself;
            # without this the handshake never starts and always times out.
            protocol.transmit()
            await asyncio.wait_for(protocol.wait_connected(), timeout=timeout)
            tls = protocol._quic.tls
            return {
                "connected": True,
                "handshake_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "session_resumed": bool(tls.session_resumed),
                "early_data_offered": ticket.max_early_data_size is not None,
                "early_data_accepted": bool(tls.early_data_accepted),
            }
    except asyncio.TimeoutError:
        return {"connected": False, "error": f"resumption handshake timed out after {timeout}s"}
    except Exception as e:
        return {"connected": False, "error": f"{type(e).__name__}: {e}"}


async def perform_zero_rtt_test(
    host: str,
    port: int = 443,
    alpn: Optional[List[str]] = None,
    sni: Optional[str] = None,
    verify: bool = False,
    timeout: float = 8.0,
) -> Dict[str, Any]:
    """Real 0-RTT check in three connections:
    1. full handshake and collect the server's session ticket;
    2. resume with that ticket (offers 0-RTT if the ticket permits it);
    3. resume again with the SAME ticket to see whether the server lets it be reused.
    """
    alpn = alpn or list(H3_ALPN)
    sni = sni or host
    try:
        ip = socket.gethostbyname(host)
    except Exception as e:
        return {"success": False, "stage": "dns", "error": f"DNS resolution failed: {e}"}

    tickets: List[Any] = []
    config = _build_config(alpn, verify)
    config.server_name = sni
    t0 = time.perf_counter()
    try:
        async with connect(host, port, configuration=config, create_protocol=_QuietProtocol, wait_connected=False,
                           session_ticket_handler=tickets.append) as protocol:
            # connect(wait_connected=False) does not send the Initial by itself;
            # without this the handshake never starts and always times out.
            protocol.transmit()
            await asyncio.wait_for(protocol.wait_connected(), timeout=timeout)
            first_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            # Servers send NewSessionTicket after the handshake; give it a moment.
            try:
                await asyncio.wait_for(protocol.ping(), timeout=2.0)
            except Exception:
                pass
            for _ in range(20):
                if tickets:
                    break
                await asyncio.sleep(0.05)
    except asyncio.TimeoutError:
        return {"success": False, "stage": "initial_handshake", "ip_address": ip,
                "error": f"initial QUIC handshake timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "stage": "initial_handshake", "ip_address": ip,
                "error": f"initial QUIC handshake failed: {type(e).__name__}: {e}"}

    result: Dict[str, Any] = {
        "success": True,
        "ip_address": ip,
        "initial_handshake_ms": first_ms,
        "ticket_issued": bool(tickets),
    }
    if not tickets:
        return result

    ticket = tickets[-1]
    result["ticket_lifetime_s"] = int((ticket.not_valid_after - ticket.not_valid_before).total_seconds())
    result["ticket_max_early_data"] = ticket.max_early_data_size
    result["resume_1"] = await _resume_with_ticket(host, port, alpn, sni, verify, ticket, timeout)
    result["resume_2_same_ticket"] = await _resume_with_ticket(host, port, alpn, sni, verify, ticket, timeout)
    return result


async def perform_http3_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: str = "",
    verify: bool = False,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Issue a real HTTP/3 (RFC 9114) request over QUIC and return the true response."""
    from urllib.parse import urlparse

    parsed = urlparse(url if "://" in url else f"https://{url}")
    host = parsed.hostname or "localhost"
    port = parsed.port or 443
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query

    try:
        ip = socket.gethostbyname(host)
    except Exception as e:
        return {"success": False, "engine": "aioquic-h3", "error": f"DNS resolution failed: {e}",
                "url": url}

    config = _build_config(list(H3_ALPN), verify)
    config.server_name = host

    t0 = time.perf_counter()
    try:
        async with connect(host, port, configuration=config,
                           create_protocol=_H3Client, wait_connected=False) as protocol:
            # connect(wait_connected=False) does not send the Initial by itself;
            # without this the handshake never starts and always times out.
            protocol.transmit()
            await asyncio.wait_for(protocol.wait_connected(), timeout=timeout)
            handshake_ms = round((time.perf_counter() - t0) * 1000.0, 2)

            stream_id = protocol._quic.get_next_available_stream_id()
            req_headers = [
                (b":method", method.encode()),
                (b":scheme", b"https"),
                (b":authority", host.encode()),
                (b":path", path.encode()),
            ]
            for k, v in (headers or {}).items():
                if not k.lower().startswith(":"):
                    req_headers.append((k.lower().encode(), str(v).encode()))

            body_bytes = body.encode() if isinstance(body, str) else (body or b"")
            tr0 = time.perf_counter()
            events = await asyncio.wait_for(
                protocol.send_request(stream_id, req_headers, body_bytes), timeout=timeout)

            resp_headers: Dict[str, str] = {}
            resp_body = bytearray()
            for h3_event in events:
                if isinstance(h3_event, HeadersReceived):
                    for k, v in h3_event.headers:
                        resp_headers[k.decode()] = v.decode()
                elif isinstance(h3_event, DataReceived):
                    resp_body.extend(h3_event.data)

            ttfb_ms = round((time.perf_counter() - tr0) * 1000.0, 2)
            total_ms = round((time.perf_counter() - t0) * 1000.0, 2)

            tls = protocol._quic.tls
            peer_cert = getattr(tls, "_peer_certificate", None)
            status = resp_headers.get(":status", "0")

            return {
                "success": True,
                "engine": "aioquic-h3 (real HTTP/3 over QUIC)",
                "url": url,
                "method": method,
                "host": host,
                "ip_address": ip,
                "status_code": int(status) if status.isdigit() else status,
                "http_version": "HTTP/3",
                "quic_version": f"0x{getattr(protocol._quic, '_version', 0):08x}",
                "alpn_negotiated": getattr(tls, "alpn_negotiated", None),
                "cipher_suite": _cipher_suite_name(tls),
                "headers": resp_headers,
                "body": resp_body.decode("utf-8", errors="replace")[:4000],
                "body_bytes": len(resp_body),
                "handshake_ms": handshake_ms,
                "ttfb_ms": ttfb_ms,
                "total_ms": total_ms,
                "peer_certificate": _cert_summary(peer_cert),
            }
    except asyncio.TimeoutError:
        return {"success": False, "engine": "aioquic-h3", "url": url, "ip_address": ip,
                "error": f"HTTP/3 request timed out after {timeout}s (endpoint may not support HTTP/3)"}
    except Exception as e:
        return {"success": False, "engine": "aioquic-h3", "url": url, "ip_address": ip,
                "error": f"HTTP/3 request failed: {type(e).__name__}: {e}"}
