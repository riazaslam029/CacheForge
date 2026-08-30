"""
Write-Ahead Log (WAL) / Journal Engine.
Provides atomic transaction logging with os.fsync durability guarantees.
"""

import os
from typing import List, Tuple, Optional, BinaryIO

from cacheforge.records import Record, RecordType
from cacheforge.errors import DatabaseError, CorruptionError, InvalidRecordError


class Journal:
    """
    Manages the Write-Ahead Log (journal.log) file for a CacheForge database.
    """

    def __init__(self, journal_path: str):
        self.journal_path = journal_path
        self._file: Optional[BinaryIO] = None

    def open(self):
        """Open journal log in append/read mode."""
        os.makedirs(os.path.dirname(self.journal_path), exist_ok=True)
        self._file = open(self.journal_path, "a+b")

    def close(self):
        """Flush, fsync, and close journal file descriptor."""
        if self._file and not self._file.closed:
            self.flush(fsync=True)
            self._file.close()
            self._file = None

    def flush(self, fsync: bool = True):
        """Flush buffer and optionally issue os.fsync to disk."""
        if self._file and not self._file.closed:
            self._file.flush()
            if fsync:
                os.fsync(self._file.fileno())

    def write_record(self, record: Record, fsync: bool = True) -> int:
        """
        Write a single record to the WAL. Returns number of bytes written.
        """
        if not self._file or self._file.closed:
            self.open()
        
        encoded = record.encode()
        self._file.seek(0, os.SEEK_END)
        bytes_written = self._file.write(encoded)
        if fsync:
            self.flush(fsync=True)
        return bytes_written

    def append_transaction(self, records: List[Record], fsync: bool = True) -> int:
        """
        Write an atomic transaction batch framed with TX_START and TX_COMMIT.
        """
        if not records:
            return 0
        
        seq = records[0].sequence
        tx_start = Record(key="__tx_start__", value=b"", record_type=RecordType.TX_START, sequence=seq)
        tx_commit = Record(key="__tx_commit__", value=b"", record_type=RecordType.TX_COMMIT, sequence=seq)

        total_bytes = 0
        total_bytes += self.write_record(tx_start, fsync=False)
        for rec in records:
            total_bytes += self.write_record(rec, fsync=False)
        total_bytes += self.write_record(tx_commit, fsync=fsync)
        return total_bytes

    def read_all_records(self) -> List[Tuple[Record, int, int]]:
        """
        Scan all journal entries from start to finish.
        Returns list of (Record, file_offset, record_bytes_len).
        Safely stops reading if incomplete or corrupted records are encountered.
        """
        if not os.path.exists(self.journal_path):
            return []

        entries = []
        with open(self.journal_path, "rb") as f:
            offset = 0
            while True:
                f.seek(offset)
                try:
                    record, bytes_read = Record.read_from_stream(f)
                    if record is None:
                        break
                    entries.append((record, offset, bytes_read))
                    offset += bytes_read
                except (InvalidRecordError, CorruptionError):
                    # Corruption or partial write encountered at offset; stop reading
                    break
                except Exception as e:
                    raise DatabaseError(f"Unexpected error reading journal at offset {offset}: {e}")
        return entries

    def truncate(self):
        """Clear and reset journal log."""
        if self._file and not self._file.closed:
            self._file.close()
            self._file = None
        
        with open(self.journal_path, "wb") as f:
            f.truncate(0)
            f.flush()
            os.fsync(f.fileno())
        
        self.open()
