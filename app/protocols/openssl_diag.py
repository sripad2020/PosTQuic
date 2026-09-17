import ssl
import socket
import time
from typing import Dict, Any, Optional, Tuple
from app.protocols.base import BaseProtocolAdapter
from app.core.metrics import MetricsCollector

class OpenSSLAdapter(BaseProtocolAdapter):
    def __init__(self):
        super().__init__("OpenSSL Diagnostic Engine", "OPENSSL")

    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not config.get("host"):
            return False, "Target Host is required for OpenSSL diagnostic test."
        return True, None

    async def execute(
        self,
        config: Dict[str, Any],
        execution_mode: str,
        network_route: str,
        proxy_profile: Optional[Any] = None
    ) -> Dict[str, Any]:
        host = config.get("host", "cloudflare.com")
        port = int(config.get("port", 443))
        sni = config.get("sni", host)
        tls_version = config.get("tls_version", "TLS 1.3")

        start_time = time.time()
        metrics = MetricsCollector()

        # Build SSL Context with OpenSSL diagnostic extraction
        context = ssl.create_default_context()
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED

        try:
            conn = socket.create_connection((host, port), timeout=5.0)
            sock = context.wrap_socket(conn, server_hostname=sni)
            
            end_time = time.time()
            rtt = (end_time - start_time) * 1000.0

            cert = sock.getpeercert()
            cipher = sock.cipher()  # (name, protocol_version, secret_bits)
            alpn_protocol = sock.selected_alpn_protocol()
            ssl_version_used = sock.version()

            # Parse Subject & Issuer
            subject = dict(x[0] for x in cert.get('subject', ()))
            issuer = dict(x[0] for x in cert.get('issuer', ()))
            sans = [item[1] for item in cert.get('subjectAltName', ())]

            metrics.record_sample(rtt, 320, 1420)

            sock.close()

            return {
                "status": "OPENSSL_HANDSHAKE_SUCCESS",
                "host": host,
                "port": port,
                "sni": sni,
                "tls_version": ssl_version_used,
                "cipher_suite": {
                    "name": cipher[0] if cipher else "Unknown",
                    "protocol": cipher[1] if cipher else "Unknown",
                    "secret_bits": cipher[2] if cipher else 256
                },
                "alpn_negotiated": alpn_protocol or "None",
                "certificate_details": {
                    "subject_cn": subject.get('commonName'),
                    "issuer_organization": issuer.get('organizationName'),
                    "valid_from": cert.get('notBefore'),
                    "valid_to": cert.get('notAfter'),
                    "subject_alt_names": sans[:10]
                },
                "rtt_ms": round(rtt, 2),
                "metrics": metrics.get_summary()
            }
        except Exception as e:
            end_time = time.time()
            rtt = (end_time - start_time) * 1000.0
            return {
                "status": "OPENSSL_HANDSHAKE_FAILED",
                "host": host,
                "port": port,
                "error": str(e),
                "rtt_ms": round(rtt, 2),
                "metrics": metrics.get_summary()
            }
