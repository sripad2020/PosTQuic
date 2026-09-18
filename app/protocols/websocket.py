import time
import base64
import hashlib
import os
import socket
import asyncio
import ssl
from typing import Dict, Any, Optional, Tuple, List
from app.protocols.base import BaseProtocolAdapter
from app.core.metrics import MetricsCollector

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

class WebSocketAdapter(BaseProtocolAdapter):
    def __init__(self):
        super().__init__("WebSocket Protocol Engine", "WEBSOCKET")

    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not config.get("url"):
            return False, "WebSocket Target URL (ws:// or wss://) is required."
        return True, None

    async def execute(
        self,
        config: Dict[str, Any],
        execution_mode: str,
        network_route: str,
        proxy_profile: Optional[Any] = None
    ) -> Dict[str, Any]:
        url = config.get("url", "wss://echo.websocket.events")
        message = config.get("message", "Hello QUICLAB WebSocket Engine")
        
        start_time = time.perf_counter()
        metrics = MetricsCollector()
        frames = []

        if WEBSOCKETS_AVAILABLE:
            try:
                t0 = time.perf_counter()
                async with websockets.connect(url, open_timeout=5.0, close_timeout=2.0) as ws:
                    rtt_conn = (time.perf_counter() - t0) * 1000.0
                    
                    # Outbound Frame 1 (Text)
                    t_msg = time.perf_counter()
                    await ws.send(message)
                    frames.append({
                        "frame_num": 1,
                        "direction": "OUT",
                        "fin": True,
                        "opcode": "0x1 (Text)",
                        "masked": True,
                        "payload_length": len(message),
                        "payload": message
                    })

                    # Inbound Frame 2 (Echo Response)
                    reply = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    rtt_msg = (time.perf_counter() - t_msg) * 1000.0
                    frames.append({
                        "frame_num": 2,
                        "direction": "IN",
                        "fin": True,
                        "opcode": "0x1 (Text)" if isinstance(reply, str) else "0x2 (Binary)",
                        "masked": False,
                        "payload_length": len(reply),
                        "payload": str(reply)[:200]
                    })

                    # Ping / Pong Frame Exchange
                    t_ping = time.perf_counter()
                    pong_waiter = await ws.ping()
                    await asyncio.wait_for(pong_waiter, timeout=2.0)
                    rtt_ping = (time.perf_counter() - t_ping) * 1000.0
                    frames.append({
                        "frame_num": 3,
                        "direction": "OUT/IN",
                        "fin": True,
                        "opcode": "0x9 (Ping) / 0xA (Pong)",
                        "rtt_ping_ms": round(rtt_ping, 2),
                        "payload": "PING_PONG_ACKNOWLEDGED"
                    })

                    rtt_total = (time.perf_counter() - start_time) * 1000.0
                    metrics.record_sample(rtt_msg, len(message), len(str(reply)))

                    return {
                        "status": "WS_CONNECTED",
                        "url": url,
                        "handshake_status": "101 Switching Protocols",
                        "subprotocol": ws.subprotocol or "None",
                        "rtt_connection_ms": round(rtt_conn, 2),
                        "rtt_roundtrip_ms": round(rtt_msg, 2),
                        "frame_inspector": frames,
                        "metrics": metrics.get_summary()
                    }
            except Exception as ws_err:
                pass

        # Fallback to direct socket-level RFC 6455 WebSocket Handshake Probe
        try:
            t0 = time.perf_counter()
            is_secure = url.startswith("wss://")
            clean_url = url.replace("wss://", "").replace("ws://", "")
            host_part = clean_url.split("/")[0]
            path = "/" + "/".join(clean_url.split("/")[1:]) if "/" in clean_url else "/"
            
            if ":" in host_part:
                host, port_s = host_part.split(":")
                port = int(port_s)
            else:
                host = host_part
                port = 443 if is_secure else 80

            sec_key = base64.b64encode(os.urandom(16)).decode("utf-8")
            sec_accept_expected = base64.b64encode(
                hashlib.sha1((sec_key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("utf-8")).digest()
            ).decode("utf-8")

            req = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}:{port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {sec_key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            ).encode("utf-8")

            loop = asyncio.get_event_loop()
            conn = await loop.run_in_executor(
                None, lambda: socket.create_connection((host, port), timeout=4.0)
            )

            if is_secure:
                ctx = ssl.create_default_context()
                conn = ctx.wrap_socket(conn, server_hostname=host)

            conn.sendall(req)
            resp_data = conn.recv(4096).decode("utf-8", errors="ignore")
            rtt = (time.perf_counter() - t0) * 1000.0
            conn.close()

            accept_header = "Not Found"
            for line in resp_data.split("\r\n"):
                if line.lower().startswith("sec-websocket-accept:"):
                    accept_header = line.split(":", 1)[1].strip()

            metrics.record_sample(rtt, len(req), len(resp_data))

            return {
                "status": "WS_HANDSHAKE_SUCCESS" if "101" in resp_data else "WS_HANDSHAKE_PROBED",
                "url": url,
                "handshake_status": resp_data.split("\r\n")[0] if resp_data else "No response",
                "sec_websocket_key": sec_key,
                "sec_websocket_accept": accept_header,
                "accept_validation": "VALID" if accept_header == sec_accept_expected else "MISMATCH_OR_PROBED",
                "rtt_ms": round(rtt, 2),
                "metrics": metrics.get_summary()
            }
        except Exception as sock_err:
            rtt = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "WS_CONNECTION_FAILED",
                "url": url,
                "error": f"WebSocket handshake failed: {str(sock_err)}",
                "rtt_ms": round(rtt, 2),
                "metrics": metrics.get_summary()
            }

