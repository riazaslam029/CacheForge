"""
Time-To-Live (TTL) & Expiration Subsystem.
Provides lazy expiration checks, remaining TTL calculations, and cleanup routines.
"""

import time
from typing import Optional

from cacheforge.records import Record


class TTLEngine:
    """
    Manages key expiration calculation, lazy TTL validation, and persist logic.
    """

    @staticmethod
    def now_us() -> int:
        """Current microsecond Unix timestamp."""
        return int(time.time() * 1_000_000)

    @classmethod
    def calculate_expire_us(cls, ttl_seconds: Optional[float]) -> int:
        """
        Calculate microsecond expiration epoch timestamp given TTL seconds.
        Returns 0 if ttl_seconds is None or <= 0 (meaning infinite retention).
        """
        if ttl_seconds is None or ttl_seconds <= 0:
            return 0
        return cls.now_us() + int(ttl_seconds * 1_000_000)

    @classmethod
    def is_expired(cls, record: Optional[Record], now_us: Optional[int] = None) -> bool:
        """
        Check if a record has passed its expiration timestamp.
        """
        if record is None:
            return True
        if record.expire_us == 0:
            return False
        current_us = now_us if now_us is not None else cls.now_us()
        return current_us >= record.expire_us

    @classmethod
    def remaining_ttl_seconds(cls, record: Record, now_us: Optional[int] = None) -> float:
        """
        Returns remaining TTL in seconds.
        Returns -1.0 if the record has no TTL (infinite).
        Returns 0.0 if the record has already expired.
        """
        if record.expire_us == 0:
            return -1.0
        current_us = now_us if now_us is not None else cls.now_us()
        if current_us >= record.expire_us:
            return 0.0
        return (record.expire_us - current_us) / 1_000_000.0
