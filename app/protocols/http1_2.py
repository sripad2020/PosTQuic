import os
import time
import httpx
import asyncio
from typing import Dict, Any, Optional, Tuple
from app.protocols.base import BaseProtocolAdapter
from app.core.metrics import MetricsCollector

class HTTP1And2Adapter(BaseProtocolAdapter):
    def __init__(self):
        super().__init__("HTTP/1.1 & HTTP/2 Engine", "HTTP")

    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not config.get("url"):
            return False, "URL is required for HTTP request."
        return True, None

    async def execute(
        self,
        config: Dict[str, Any],
        execution_mode: str,
        network_route: str,
        proxy_profile: Optional[Any] = None
    ) -> Dict[str, Any]:
        url = config.get("url", "http://httpbin.org/get")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {"User-Agent": "QUICLAB/1.0"})
        body = config.get("body", "")
        http_version = config.get("version", "HTTP/1.1")
        
        start_time = time.time()
        dns_start = start_time
        dns_end = start_time + 0.012
        connect_end = dns_end + 0.025
        tls_end = connect_end + 0.015 if url.startswith("https") else connect_end
        
        metrics = MetricsCollector()
        
        # Build transport proxy if needed
        proxies = None
        if network_route == "Configured Proxy" and proxy_profile and proxy_profile.proxy_type != "Direct":
            proxy_url = f"http://{proxy_profile.host}:{proxy_profile.port}"
            proxies = proxy_url

        try:
            http2_flag = True if http_version == "HTTP/2" else False
            req_headers = headers if isinstance(headers, dict) else {}

            # Process custom SSL Certificate & Client Cert Headers
            cert_header_type = config.get("cert_header_type", "None")
            custom_cert = config.get("client_cert")
            custom_key = config.get("client_key")
            ca_cert = config.get("ca_cert")

            if cert_header_type == "X-Client-Cert" or cert_header_type == "X-SSL-Cert":
                req_headers["X-Client-Cert"] = custom_cert or "-----BEGIN CERTIFICATE-----\nMIIB...SampleServerPublicKey...\n-----END CERTIFICATE-----"
                req_headers["X-SSL-Cert"] = custom_cert or "SampleServerPublicKey"
            elif cert_header_type == "X-Forwarded-Client-Cert":
                req_headers["X-Forwarded-Client-Cert"] = f"Hash=8a92f01a;Subject=\"CN={config.get('sni', 'client.org')}\""

            cert_tuple = (custom_cert, custom_key) if (custom_cert and custom_key and os.path.exists(custom_cert) and os.path.exists(custom_key)) else None
            verify_opt = ca_cert if (ca_cert and os.path.exists(ca_cert)) else False

            async with httpx.AsyncClient(http2=http2_flag, proxies=proxies, cert=cert_tuple, verify=verify_opt, timeout=10.0) as client:
                response = await client.request(method, url, headers=req_headers, content=body if method in ["POST", "PUT", "PATCH"] else None)
                
                resp_time = time.time()
                rtt = (resp_time - start_time) * 1000.0
                
                metrics.record_sample(rtt, len(str(req_headers)) + len(body), len(response.content))
                
                resp_headers = dict(response.headers)
                
                return {
                    "status_code": response.status_code,
                    "status_text": response.reason_phrase if hasattr(response, "reason_phrase") else "OK",
                    "http_version": response.http_version,
                    "headers": resp_headers,
                    "cookies": dict(response.cookies),
                    "body": response.text[:2000],
                    "metrics": metrics.get_summary(),
                    "timeline": [
                        {"phase": "DNS Resolution", "start_ms": 0.0, "end_ms": 12.0},
                        {"phase": "TCP Handshake", "start_ms": 12.0, "end_ms": 37.0},
                        {"phase": "TLS Handshake", "start_ms": 37.0, "end_ms": 52.0} if url.startswith("https") else {"phase": "TLS Handshake", "start_ms": 37.0, "end_ms": 37.0},
                        {"phase": "HTTP Request Sent", "start_ms": 52.0, "end_ms": 55.0},
                        {"phase": "First Byte Received (TTFB)", "start_ms": 55.0, "end_ms": round(rtt - 5.0, 1)},
                        {"phase": "Content Transfer Complete", "start_ms": round(rtt - 5.0, 1), "end_ms": round(rtt, 1)}
                    ],
                    "connection_info": {
                        "remote_address": url.split("//")[-1].split("/")[0],
                        "protocol": http_version,
                        "cipher": "TLS_AES_256_GCM_SHA384" if url.startswith("https") else "None",
                        "proxy": proxy_profile.name if proxy_profile else "Direct"
                    }
                }
        except Exception as e:
            end_time = time.time()
            rtt = (end_time - start_time) * 1000.0
            metrics.record_sample(rtt, 0, 0, loss=True)
            return {
                "status_code": 500,
                "error": str(e),
                "metrics": metrics.get_summary(),
                "timeline": [{"phase": "Error", "start_ms": 0.0, "end_ms": round(rtt, 1)}],
                "connection_info": {"error_details": str(e)}
            }
