"""
Database Compaction Engine.
Purges obsolete record versions, deleted tombstone entries, and expired TTL keys.
Uses atomic directory/file replacement for crash-safe compaction.
"""

from dataclasses import dataclass, field
import os
import shutil
import tempfile
from typing import Dict, Tuple, List, Any

from cacheforge.records import Record, RecordType
from cacheforge.ttl import TTLEngine
from cacheforge.errors import DatabaseError


@dataclass
class CompactionReport:
    before_bytes: int = 0
    after_bytes: int = 0
    records_before: int = 0
    records_after: int = 0
    retained_keys: int = 0
    purged_expired: int = 0
    purged_deleted: int = 0

    @property
    def bytes_saved(self) -> int:
        return max(0, self.before_bytes - self.after_bytes)

    @property
    def ratio_percent(self) -> float:
        if self.before_bytes == 0:
            return 0.0
        return (self.bytes_saved / self.before_bytes) * 100.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "before_bytes": self.before_bytes,
            "after_bytes": self.after_bytes,
            "bytes_saved": self.bytes_saved,
            "space_reduction_percent": round(self.ratio_percent, 2),
            "records_before": self.records_before,
            "records_after": self.records_after,
            "retained_keys": self.retained_keys,
            "purged_expired": self.purged_expired,
            "purged_deleted": self.purged_deleted
        }

    def format_text(self) -> str:
        lines = [
            "CacheForge Compaction Summary",
            "=============================",
            f"Original data size:    {self.before_bytes:,} B",
            f"Compacted data size:   {self.after_bytes:,} B",
            f"Space saved:           {self.bytes_saved:,} B ({self.ratio_percent:.1f}%)",
            f"Records before:        {self.records_before}",
            f"Active keys retained:  {self.retained_keys}",
            f"Expired keys purged:   {self.purged_expired}",
            f"Deleted keys purged:   {self.purged_deleted}"
        ]
        return "\n".join(lines)


class Compactor:
    """
    Executes offline/online atomic database compaction.
    """

    @classmethod
    def compact_database(cls, db_dir: str) -> CompactionReport:
        report = CompactionReport()
        data_log_path = os.path.join(db_dir, "data.log")
        journal_log_path = os.path.join(db_dir, "journal.log")

        if not os.path.exists(data_log_path):
            return report

        report.before_bytes = os.path.getsize(data_log_path)
        if os.path.exists(journal_log_path):
            report.before_bytes += os.path.getsize(journal_log_path)

        # 1. Scan active state and filter records
        active_records: Dict[str, Record] = {}
        now_us = TTLEngine.now_us()
        deleted_count = 0
        total_records_scanned = 0

        with open(data_log_path, "rb") as f:
            offset = 0
            while True:
                f.seek(offset)
                rec, bytes_read = Record.read_from_stream(f)
                if rec is None:
                    break
                total_records_scanned += 1
                offset += bytes_read

                if rec.record_type == RecordType.SET:
                    active_records[rec.key] = rec
                elif rec.record_type == RecordType.DELETE:
                    deleted_count += 1
                    active_records.pop(rec.key, None)

        report.records_before = total_records_scanned

        # Filter out expired records
        retained_records: List[Record] = []
        expired_count = 0
        for key, rec in active_records.items():
            if TTLEngine.is_expired(rec, now_us=now_us):
                expired_count += 1
            else:
                retained_records.append(rec)

        report.purged_expired = expired_count
        report.purged_deleted = deleted_count
        report.retained_keys = len(retained_records)
        report.records_after = len(retained_records)

        # 2. Write to temporary compacted file
        tmp_data_log = data_log_path + ".compact.tmp"
        with open(tmp_data_log, "wb") as f:
            for rec in retained_records:
                f.write(rec.encode())
            f.flush()
            os.fsync(f.fileno())

        report.after_bytes = os.path.getsize(tmp_data_log)

        # 3. Atomic File Swap
        os.replace(tmp_data_log, data_log_path)

        # Clear journal log since compaction produces clean data log
        if os.path.exists(journal_log_path):
            with open(journal_log_path, "wb") as f:
                f.truncate(0)
                f.flush()
                os.fsync(f.fileno())

        return report
