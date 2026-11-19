import time
from typing import Dict, Any, Optional, Tuple
from app.protocols.base import BaseProtocolAdapter
from app.core.metrics import MetricsCollector
from app.protocols.quic import QUICAdapter
from app.protocols.quic_real import perform_http3_request, AIOQUIC_AVAILABLE


class HTTP3Adapter(BaseProtocolAdapter):
    """
    HTTP/3 (RFC 9114) engine.

    Primary path: a real HTTP/3 request over a genuine QUIC connection via
    aioquic — the returned status, headers and body are the server's actual
    H3 response, and the negotiated ALPN/cipher/cert are real.

    Fallback path (aioquic unavailable or QUIC unreachable in this network):
    the underlying QUIC adapter's honest probe/handshake report, with the
    HTTP layer clearly marked as not completed over HTTP/3.
    """
    def __init__(self):
        super().__init__("HTTP/3 Protocol Engine (aioquic)", "HTTP/3")
        self.quic_engine = QUICAdapter()

    def supports_migration(self) -> bool:
        return True

    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not config.get("url"):
            return False, "URL is required for HTTP/3 request."
        return True, None

    async def execute(
        self,
        config: Dict[str, Any],
        execution_mode: str,
        network_route: str,
        proxy_profile: Optional[Any] = None,
    ) -> Dict[str, Any]:
        url = config.get("url", "https://cloudflare-quic.com/")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {"user-agent": "QUICLAB/2.0 (aioquic HTTP/3 Engine)"})
        body = config.get("body", "")
        verify = bool(config.get("verify_tls", False))

        t0 = time.perf_counter()

        if AIOQUIC_AVAILABLE:
            real = await perform_http3_request(
                method, url, headers if isinstance(headers, dict) else {}, body, verify=verify
            )
            if real.get("success"):
                return self._from_real_h3(real)
            fallback_reason = real.get("error", "HTTP/3 request did not complete")
        else:
            fallback_reason = "aioquic not installed"

        # Honest fallback: report the real QUIC-layer outcome, mark H3 as not done.
        host = url.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        quic_res = await self.quic_engine.execute(
            {"host": host, "port": 443, "alpn": "h3", "sni": host, "verify_tls": verify},
            execution_mode, network_route, proxy_profile,
        )
        rtt = round((time.perf_counter() - t0) * 1000.0, 2)
        return {
            "status": "HTTP3_NOT_COMPLETED",
            "http_version": "HTTP/3 (attempted)",
            "http3_completed": False,
            "reason": fallback_reason,
            "status_code": None,
            "body": f"Real HTTP/3 request could not complete: {fallback_reason}",
            "rtt_ms": rtt,
            "quic_details": quic_res,
            "metrics": quic_res.get("metrics", {}),
        }

    def _from_real_h3(self, real: Dict[str, Any]) -> Dict[str, Any]:
        metrics = MetricsCollector()
        metrics.record_sample(real.get("handshake_ms", 0.0), 200, real.get("body_bytes", 0))
        if real.get("ttfb_ms"):
            metrics.record_sample(real["ttfb_ms"], 0, 0)

        status = real.get("status_code", 0)
        correlation = {
            "application_layer": {
                "protocol": "HTTP/3",
                "method": real.get("method"),
                "url": real.get("url"),
                "status_code": status,
                "headers": real.get("headers", {}),
                "body_preview": real.get("body", "")[:500],
            },
            "quic_stream_layer": {
                "stream_id": 0,
                "stream_type": "Request Stream (QPACK encoded)",
                "bytes_received": real.get("body_bytes", 0),
            },
            "security_layer": {
                "tls_version": "TLS 1.3",
                "cipher_suite": real.get("cipher_suite"),
                "alpn": real.get("alpn_negotiated"),
                "peer_certificate_cn": real.get("peer_certificate", {}).get("subject_cn"),
            },
            "transport_layer": {
                "protocol": "QUIC/UDP",
                "quic_version": real.get("quic_version"),
                "dst_endpoint": f"{real.get('host')}:443",
                "ip": real.get("ip_address"),
            },
        }

        return {
            "status": "HTTP3_RESPONSE_COMPLETE",
            "engine": real.get("engine"),
            "http3_completed": True,
            "status_code": status,
            "status_text": "OK" if status == 200 else "HTTP Response",
            "http_version": "HTTP/3",
            "headers": real.get("headers", {}),
            "body": real.get("body", ""),
            "body_bytes": real.get("body_bytes", 0),
            "handshake_ms": real.get("handshake_ms"),
            "ttfb_ms": real.get("ttfb_ms"),
            "rtt_ms": real.get("total_ms"),
            "cipher_suite": real.get("cipher_suite"),
            "alpn_negotiated": real.get("alpn_negotiated"),
            "quic_version": real.get("quic_version"),
            "certificate": real.get("peer_certificate", {}),
            "correlation": correlation,
            "metrics": metrics.get_summary(),
        }


http3_adapter_instance = HTTP3Adapter()
