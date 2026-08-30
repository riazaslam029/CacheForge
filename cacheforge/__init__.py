"""
CacheForge — Zero-dependency embedded storage engine with WAL, search, TTL, and crash recovery.
"""

from cacheforge.database import CacheForgeDB
from cacheforge.records import Record, RecordType
from cacheforge.errors import (
    CacheForgeError,
    DatabaseError,
    CorruptionError,
    RecoveryError,
    InvalidRecordError,
    KeyNotFoundError,
    LockError,
    TTLError
)

__version__ = "1.0.0"

__all__ = [
    "CacheForgeDB",
    "Record",
    "RecordType",
    "CacheForgeError",
    "DatabaseError",
    "CorruptionError",
    "RecoveryError",
    "InvalidRecordError",
    "KeyNotFoundError",
    "LockError",
    "TTLError",
    "__version__"
]
