"""
Concurrency and File Locking Engine.
Provides thread-safe reentrant locks and OS process-level file locking (fcntl.flock / lockfile fallback).
"""

import os
import sys
import threading
import time
from typing import Optional

from cacheforge.errors import LockError

try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False


class DatabaseLock:
    """
    Coordinates process-level and thread-level locking for CacheForge database directories.
    Provides mutual exclusion for writers and multi-reader coordination.
    Handles reentrant lock acquisitions within the same thread seamlessly.
    """

    def __init__(self, lock_file_path: str, timeout: float = 10.0):
        self.lock_file_path = lock_file_path
        self.timeout = timeout
        self._thread_lock = threading.RLock()
        self._file_fd: Optional[int] = None
        self._lock_count = 0

    def acquire(self, exclusive: bool = True) -> bool:
        """
        Acquire thread lock and process file lock.
        Supports reentrant locking for the same thread.
        """
        start_time = time.time()

        # 1. Acquire thread reentrant lock
        if not self._thread_lock.acquire(timeout=self.timeout):
            raise LockError(f"Failed to acquire thread lock within {self.timeout}s")

        self._lock_count += 1

        # Only acquire OS process file lock on the first outermost lock call
        if self._lock_count == 1:
            try:
                lock_dir = os.path.dirname(self.lock_file_path)
                if lock_dir:
                    os.makedirs(lock_dir, exist_ok=True)

                flags = os.O_RDWR | os.O_CREAT
                self._file_fd = os.open(self.lock_file_path, flags, 0o666)

                if HAS_FCNTL:
                    operation = fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH
                    while True:
                        try:
                            fcntl.flock(self._file_fd, operation | fcntl.LOCK_NB)
                            break
                        except (IOError, OSError):
                            if time.time() - start_time >= self.timeout:
                                raise LockError(
                                    f"Failed to acquire process file lock ({self.lock_file_path}) "
                                    f"within {self.timeout} seconds"
                                )
                            time.sleep(0.01)
                else:
                    # Lock file fallback for non-POSIX platforms
                    lock_flag_file = self.lock_file_path + ".flag"
                    while True:
                        try:
                            fd = os.open(lock_flag_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
                            os.close(fd)
                            break
                        except FileExistsError:
                            if time.time() - start_time >= self.timeout:
                                raise LockError(
                                    f"Failed to acquire fallback lock file ({lock_flag_file}) "
                                    f"within {self.timeout} seconds"
                                )
                            time.sleep(0.01)

            except Exception as e:
                self._lock_count -= 1
                self._thread_lock.release()
                if self._file_fd is not None:
                    try:
                        os.close(self._file_fd)
                    except OSError:
                        pass
                    self._file_fd = None
                if not isinstance(e, LockError):
                    raise LockError(f"Error acquiring lock on {self.lock_file_path}: {e}")
                raise e

        return True

    def release(self):
        """Release process file lock and thread lock when outer count reaches zero."""
        if self._lock_count <= 0:
            return

        self._lock_count -= 1

        # Only release OS process file lock when outermost lock count reaches 0
        if self._lock_count == 0:
            try:
                if self._file_fd is not None:
                    if HAS_FCNTL:
                        try:
                            fcntl.flock(self._file_fd, fcntl.LOCK_UN)
                        except (IOError, OSError):
                            pass
                    else:
                        lock_flag_file = self.lock_file_path + ".flag"
                        if os.path.exists(lock_flag_file):
                            try:
                                os.remove(lock_flag_file)
                            except OSError:
                                pass
                    try:
                        os.close(self._file_fd)
                    except OSError:
                        pass
                    self._file_fd = None
            finally:
                self._thread_lock.release()
        else:
            self._thread_lock.release()

    def __enter__(self):
        self.acquire(exclusive=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
