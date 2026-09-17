import time
import uuid
from typing import Dict, Any, List, Optional

class PacketCaptureItem:
    def __init__(self, packet_num: int, direction: str, packet_type: str, payload_size: int,
                 connection_id: str, encryption_level: str, frames: List[Dict[str, Any]], path_info: str = "127.0.0.1:9000 -> 10.0.0.1:443"):
        self.id = str(uuid.uuid4())[:8]
        self.packet_num = packet_num
        self.timestamp = time.strftime("%H:%M:%S.") + f"{int((time.time() % 1) * 1000):03d}"
        self.direction = direction  # "OUT" or "IN"
        self.packet_type = packet_type  # "Initial", "Handshake", "0-RTT", "1-RTT (Short)"
        self.payload_size = payload_size
        self.connection_id = connection_id
        self.encryption_level = encryption_level  # "Initial", "Handshake", "Application"
        self.frames = frames
        self.path_info = path_info

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "packet_num": self.packet_num,
            "timestamp": self.timestamp,
            "direction": self.direction,
            "packet_type": self.packet_type,
            "payload_size": self.payload_size,
            "connection_id": self.connection_id,
            "encryption_level": self.encryption_level,
            "frames": self.frames,
            "path_info": self.path_info
        }

class CaptureEngine:
    def __init__(self):
        self.packets: List[PacketCaptureItem] = []

    def add_packet(self, packet: PacketCaptureItem):
        self.packets.append(packet)

    def get_packets(self) -> List[Dict[str, Any]]:
        return [p.to_dict() for p in self.packets]

    def clear(self):
        self.packets = []
