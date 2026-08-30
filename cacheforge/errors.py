"""
CacheForge Exception Hierarchy.
All exceptions derive from CacheForgeError for consistent, clean error handling.
"""


class CacheForgeError(Exception):
    """Base exception class for all CacheForge errors."""

    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code

    def __str__(self) -> str:
        return self.message


class DatabaseError(CacheForgeError):
    """Raised when general database operations fail."""

    def __init__(self, message: str, exit_code: int = 2):
        super().__init__(message, exit_code=exit_code)


class KeyNotFoundError(CacheForgeError):
    """Raised when a requested key does not exist or has expired."""

    def __init__(self, key: str, exit_code: int = 3):
        super().__init__(f"Key not found: '{key}'", exit_code=exit_code)
        self.key = key


class InvalidRecordError(CacheForgeError):
    """Raised when a record has an invalid format or header."""

    def __init__(self, message: str, exit_code: int = 4):
        super().__init__(message, exit_code=exit_code)


class CorruptionError(CacheForgeError):
    """Raised when checksum or payload validation fails."""

    def __init__(self, message: str, exit_code: int = 5):
        super().__init__(message, exit_code=exit_code)


class RecoveryError(CacheForgeError):
    """Raised when database recovery encounters unrecoverable corruption."""

    def __init__(self, message: str, exit_code: int = 6):
        super().__init__(message, exit_code=exit_code)


class LockError(CacheForgeError):
    """Raised when acquiring thread or process file locks fails."""

    def __init__(self, message: str, exit_code: int = 7):
        super().__init__(message, exit_code=exit_code)


class TTLError(CacheForgeError):
    """Raised when an invalid TTL value or expiration operation occurs."""

    def __init__(self, message: str, exit_code: int = 8):
        super().__init__(message, exit_code=exit_code)
