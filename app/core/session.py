import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional

class SessionState(str, Enum):
    CREATED = "CREATED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    ACTIVE = "ACTIVE"
    CLOSING = "CLOSING"
    CLOSED = "CLOSED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
    
    # QUIC Specific states
    INITIAL = "INITIAL"
    HANDSHAKING = "HANDSHAKING"
    HANDSHAKE_COMPLETE = "HANDSHAKE_COMPLETE"
    PATH_VALIDATING = "PATH_VALIDATING"
    MIGRATING = "MIGRATING"
    DRAINING = "DRAINING"

class ProtocolSession:
    def __init__(self, session_id: str, protocol: str, target: str, execution_mode: str, network_route: str):
        self.session_id = session_id
        self.protocol = protocol
        self.target = target
        self.execution_mode = execution_mode
        self.network_route = network_route
        self.state = SessionState.CREATED
        self.created_at = time.time()
        self.updated_at = time.time()
        self.events: List[Dict[str, Any]] = []
        self.metrics: Dict[str, Any] = {
            "rtt_ms": 0.0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "packets_sent": 0,
            "packets_received": 0,
            "packet_loss_pct": 0.0,
            "active_streams": 0
        }

    def transition_to(self, new_state: SessionState, event_description: str = ""):
        old_state = self.state
        self.state = new_state
        self.updated_at = time.time()
        event = {
            "timestamp": time.strftime("%H:%M:%S.") + f"{int((time.time() % 1) * 1000):03d}",
            "from_state": old_state.value,
            "to_state": new_state.value,
            "description": event_description
        }
        self.events.append(event)
        return event

    def record_metrics(self, rtt: float, bytes_sent: int, bytes_recv: int, packets_sent: int = 1, packets_recv: int = 1):
        self.metrics["rtt_ms"] = round(rtt, 2)
        self.metrics["bytes_sent"] += bytes_sent
        self.metrics["bytes_received"] += bytes_recv
        self.metrics["packets_sent"] += packets_sent
        self.metrics["packets_received"] += packets_recv

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "protocol": self.protocol,
            "target": self.target,
            "execution_mode": self.execution_mode,
            "network_route": self.network_route,
            "state": self.state.value,
            "created_at": self.created_at,
            "events": self.events,
            "metrics": self.metrics
        }
