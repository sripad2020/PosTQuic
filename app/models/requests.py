"""
Request/configuration models shared across engines.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class FuzzerVector(str, Enum):
    """QUIC/transport fuzzing mutation vectors (RFC 9000 frame space)."""
    STREAM_OFFSET_OVERFLOW = "STREAM_OFFSET_OVERFLOW"
    ACK_RANGE_INFLATION = "ACK_RANGE_INFLATION"
    CID_TRUNCATION = "CID_TRUNCATION"
    MALFORMED_CRYPTO_FRAME = "MALFORMED_CRYPTO_FRAME"
    RESET_STORM = "RESET_STORM"
    ZERO_RTT_REPLAY = "ZERO_RTT_REPLAY"

    @classmethod
    def all(cls) -> "List[FuzzerVector]":
        return list(cls)


@dataclass
class FuzzRequest:
    """A single fuzzing campaign definition supplied by the caller."""
    host: str
    port: int = 4433
    protocol: str = "QUIC"
    vectors: List[FuzzerVector] = field(default_factory=FuzzerVector.all)
    iterations_per_vector: int = 10
    timeout_seconds: float = 2.0

    def __post_init__(self):
        # Normalise string vectors into enum members.
        norm: List[FuzzerVector] = []
        for v in self.vectors:
            if isinstance(v, FuzzerVector):
                norm.append(v)
            else:
                try:
                    norm.append(FuzzerVector(str(v)))
                except ValueError:
                    continue
        self.vectors = norm or FuzzerVector.all()
