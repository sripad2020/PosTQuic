import time
import random
from typing import Dict, Any, List

class MetricsCollector:
    def __init__(self):
        self.rtt_history: List[float] = []
        self.throughput_bps: float = 0.0
        self.bytes_sent: int = 0
        self.bytes_received: int = 0
        self.packets_sent: int = 0
        self.packets_received: int = 0
        self.packet_loss_count: int = 0
        self.retransmissions: int = 0
        self.congestion_window_bytes: int = 14600
        self.active_streams: int = 0

    def record_sample(self, rtt_ms: float, bytes_tx: int, bytes_rx: int, loss: bool = False, retrans: bool = False):
        self.rtt_history.append(rtt_ms)
        if len(self.rtt_history) > 100:
            self.rtt_history.pop(0)
            
        self.bytes_sent += bytes_tx
        self.bytes_received += bytes_rx
        self.packets_sent += 1
        if not loss:
            self.packets_received += 1
        else:
            self.packet_loss_count += 1
            
        if retrans:
            self.retransmissions += 1

    def get_summary(self) -> Dict[str, Any]:
        avg_rtt = sum(self.rtt_history) / max(1, len(self.rtt_history))
        rtt_var = (sum((x - avg_rtt)**2 for x in self.rtt_history) / max(1, len(self.rtt_history))) ** 0.5
        loss_pct = (self.packet_loss_count / max(1, self.packets_sent)) * 100.0
        
        return {
            "latest_rtt_ms": round(self.rtt_history[-1], 2) if self.rtt_history else 0.0,
            "avg_rtt_ms": round(avg_rtt, 2),
            "rtt_variance": round(rtt_var, 2),
            "bytes_sent": self.bytes_sent,
            "bytes_received": self.bytes_received,
            "packets_sent": self.packets_sent,
            "packets_received": self.packets_received,
            "packet_loss_pct": round(loss_pct, 2),
            "retransmissions": self.retransmissions,
            "cwnd_bytes": self.congestion_window_bytes,
            "active_streams": self.active_streams
        }
