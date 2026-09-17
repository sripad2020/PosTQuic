import time
import socket
import asyncio
from typing import Dict, Any, Optional, Tuple
from app.protocols.base import BaseProtocolAdapter
from app.core.metrics import MetricsCollector

class RawTCPAdapter(BaseProtocolAdapter):
    def __init__(self):
        super().__init__("Raw TCP Socket Engine", "RAW TCP")

    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not config.get("host") or not config.get("port"):
            return False, "Host and Port are required for Raw TCP testing."
        return True, None

    async def execute(
        self,
        config: Dict[str, Any],
        execution_mode: str,
        network_route: str,
        proxy_profile: Optional[Any] = None
    ) -> Dict[str, Any]:
        host = config.get("host", "127.0.0.1")
        port = int(config.get("port", 80))
        payload = config.get("payload", "PING TCP")
        payload_mode = config.get("payload_mode", "Text")
        tcp_nodelay = config.get("tcp_nodelay", True)
        keepalive = config.get("keepalive", True)

        start_time = time.time()
        metrics = MetricsCollector()

        # Format payload
        raw_bytes = payload.encode("utf-8")
        if payload_mode == "Hex":
            try:
                raw_bytes = bytes.fromhex(payload.replace(" ", ""))
            except Exception:
                raw_bytes = payload.encode("utf-8")

        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=5.0
            )
            connect_time = time.time()
            conn_duration = (connect_time - start_time) * 1000.0

            sock = writer.get_extra_info("socket")
            if sock and tcp_nodelay:
                try:
                    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                except Exception:
                    pass

            writer.write(raw_bytes)
            await writer.drain()

            tx_bytes = len(raw_bytes)

            try:
                data = await asyncio.wait_for(reader.read(4096), timeout=3.0)
                rx_bytes = len(data)
                resp_text = data.decode("utf-8", errors="replace")
            except asyncio.TimeoutError:
                rx_bytes = 0
                resp_text = "<Read Timeout - No response data returned>"

            end_time = time.time()
            rtt = (end_time - connect_time) * 1000.0

            writer.close()
            await writer.wait_closed()

            metrics.record_sample(rtt, tx_bytes, rx_bytes)

            return {
                "status": "TCP_CONNECTED",
                "local_endpoint": writer.get_extra_info("sockname") if sock else "127.0.0.1:auto",
                "remote_endpoint": f"{host}:{port}",
                "connect_duration_ms": round(conn_duration, 2),
                "rtt_ms": round(rtt, 2),
                "bytes_sent": tx_bytes,
                "bytes_received": rx_bytes,
                "payload_mode": payload_mode,
                "response_payload": resp_text[:1000],
                "tcp_flags": {
                    "TCP_NODELAY": tcp_nodelay,
                    "SO_KEEPALIVE": keepalive
                },
                "metrics": metrics.get_summary()
            }
        except Exception as e:
            return {
                "status": "TCP_ERROR",
                "error": str(e),
                "remote_endpoint": f"{host}:{port}",
                "rtt_ms": 0.0,
                "bytes_sent": len(raw_bytes),
                "bytes_received": 0,
                "metrics": metrics.get_summary()
            }
