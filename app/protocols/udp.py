import time
import socket
import asyncio
from typing import Dict, Any, Optional, Tuple
from app.protocols.base import BaseProtocolAdapter
from app.core.metrics import MetricsCollector

class RawUDPAdapter(BaseProtocolAdapter):
    def __init__(self):
        super().__init__("Raw UDP Datagram Engine", "RAW UDP")

    def validate_configuration(self, config: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if not config.get("host") or not config.get("port"):
            return False, "Destination IP/Host and Port are required for UDP datagram test."
        return True, None

    async def execute(
        self,
        config: Dict[str, Any],
        execution_mode: str,
        network_route: str,
        proxy_profile: Optional[Any] = None
    ) -> Dict[str, Any]:
        host = config.get("host", "127.0.0.1")
        port = int(config.get("port", 53))
        packet_count = int(config.get("packet_count", 5))
        packet_size = int(config.get("packet_size", 64))
        ttl = int(config.get("ttl", 64))
        payload_text = config.get("payload", "QUICLAB_UDP_TEST_PING")
        timeout = float(config.get("timeout", 1.0))

        metrics = MetricsCollector()
        rtt_list = []
        packets_sent = 0
        packets_received = 0

        # Construct raw payload padding to match packet_size
        raw_payload = payload_text.encode("utf-8")
        if len(raw_payload) < packet_size:
            raw_payload += b"\x00" * (packet_size - len(raw_payload))

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        loop = asyncio.get_event_loop()

        try:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
        except Exception:
            pass

        try:
            ip = socket.gethostbyname(host)
        except Exception:
            ip = host

        for i in range(packet_count):
            t0 = time.perf_counter()
            try:
                await loop.sock_sendto(sock, raw_payload, (ip, port))
                packets_sent += 1
                
                try:
                    data, addr = await asyncio.wait_for(loop.sock_recvfrom(sock, 4096), timeout=timeout)
                    t1 = time.perf_counter()
                    rtt_ms = round((t1 - t0) * 1000.0, 2)
                    packets_received += 1
                    rtt_list.append(rtt_ms)
                    metrics.record_sample(rtt_ms, len(raw_payload), len(data))
                except asyncio.TimeoutError:
                    t1 = time.perf_counter()
                    rtt_ms = round((t1 - t0) * 1000.0, 2)
                    rtt_list.append(rtt_ms)
                    metrics.record_sample(rtt_ms, len(raw_payload), 0, loss=True)
            except Exception:
                pass
            
            await asyncio.sleep(0.01)

        sock.close()

        avg_rtt = sum(rtt_list) / max(1, len(rtt_list)) if rtt_list else 0.0
        jitter = max(0.0, (sum(abs(x - avg_rtt) for x in rtt_list) / max(1, len(rtt_list)))) if rtt_list else 0.0
        packet_loss = max(0.0, ((packets_sent - packets_received) / max(1, packets_sent)) * 100.0)

        return {
            "status": "UDP_DISPATCHED",
            "source_endpoint": "127.0.0.1:auto",
            "destination_endpoint": f"{host}:{port}",
            "ip_address": ip,
            "packets_sent": packets_sent,
            "packets_received": packets_received,
            "packet_loss_pct": round(packet_loss, 2),
            "rtt_ms": round(avg_rtt, 2),
            "jitter_ms": round(jitter, 2),
            "throughput_kbps": round((packets_sent * packet_size * 8) / max(0.1, avg_rtt), 2) if avg_rtt > 0 else 0.0,
            "ip_version": "IPv4",
            "ttl": ttl,
            "metrics": metrics.get_summary()
        }
