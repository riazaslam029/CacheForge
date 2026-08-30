"""
Data Integrity Verification Engine.
Audits binary log files, verifies record headers, validates SHA-256 checksums, and reports corruption.
"""

from dataclasses import dataclass, field
import os
from typing import List, Dict, Any

from cacheforge.records import Record, RecordType
from cacheforge.errors import InvalidRecordError, CorruptionError


@dataclass
class IntegrityReport:
    records_scanned: int = 0
    valid_records: int = 0
    corrupt_records: int = 0
    total_bytes_scanned: int = 0
    index_status: str = "VALID"
    journal_status: str = "CLEAN"
    corrupt_offsets: List[int] = field(default_factory=list)
    details: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return self.corrupt_records == 0 and self.index_status == "VALID"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "records_scanned": self.records_scanned,
            "valid_records": self.valid_records,
            "corrupt_records": self.corrupt_records,
            "total_bytes_scanned": self.total_bytes_scanned,
            "index_status": self.index_status,
            "journal_status": self.journal_status,
            "corrupt_offsets": self.corrupt_offsets,
            "details": self.details,
            "integrity": "VALID" if self.is_valid else "CORRUPTED"
        }

    def format_text(self) -> str:
        lines = [
            "CacheForge Integrity Check",
            "--------------------------",
            f"Records scanned:    {self.records_scanned}",
            f"Valid records:      {self.valid_records}",
            f"Corrupt records:    {self.corrupt_records}",
            f"Bytes scanned:      {self.total_bytes_scanned:,} B",
            f"Index status:       {self.index_status}",
            f"Journal status:     {self.journal_status}",
            f"Overall Integrity:  {'VALID' if self.is_valid else 'CORRUPTED'}"
        ]
        if self.details:
            lines.append("\nAudit Details:")
            for detail in self.details[:10]:
                lines.append(f"  - {detail}")
            if len(self.details) > 10:
                lines.append(f"  ... ({len(self.details) - 10} more items omitted)")
        return "\n".join(lines)


class IntegrityChecker:
    """
    Scans database file structures and verifies binary record checksums.
    """

    @classmethod
    def verify_database(cls, db_dir: str) -> IntegrityReport:
        report = IntegrityReport()
        data_log_path = os.path.join(db_dir, "data.log")
        journal_log_path = os.path.join(db_dir, "journal.log")

        # 1. Scan data.log
        if os.path.exists(data_log_path):
            with open(data_log_path, "rb") as f:
                offset = 0
                f.seek(0, os.SEEK_END)
                file_size = f.tell()
                f.seek(0)

                while offset < file_size:
                    f.seek(offset)
                    try:
                        record, bytes_read = Record.read_from_stream(f)
                        if record is None:
                            break
                        report.records_scanned += 1
                        report.valid_records += 1
                        report.total_bytes_scanned += bytes_read
                        offset += bytes_read
                    except (InvalidRecordError, CorruptionError) as err:
                        report.records_scanned += 1
                        report.corrupt_records += 1
                        report.corrupt_offsets.append(offset)
                        report.details.append(f"Data log offset {offset}: {err}")
                        report.index_status = "CORRUPT"
                        break
                    except Exception as e:
                        report.records_scanned += 1
                        report.corrupt_records += 1
                        report.corrupt_offsets.append(offset)
                        report.details.append(f"Data log offset {offset} unexpected error: {e}")
                        report.index_status = "CORRUPT"
                        break

        # 2. Audit journal.log
        if os.path.exists(journal_log_path) and os.path.getsize(journal_log_path) > 0:
            with open(journal_log_path, "rb") as f:
                j_offset = 0
                f.seek(0, os.SEEK_END)
                j_size = f.tell()
                f.seek(0)

                uncommitted_tx = False
                while j_offset < j_size:
                    f.seek(j_offset)
                    try:
                        record, bytes_read = Record.read_from_stream(f)
                        if record is None:
                            break
                        if record.record_type == RecordType.TX_START:
                            uncommitted_tx = True
                        elif record.record_type == RecordType.TX_COMMIT:
                            uncommitted_tx = False
                        j_offset += bytes_read
                    except Exception as err:
                        report.journal_status = "CORRUPT"
                        report.details.append(f"Journal log offset {j_offset}: {err}")
                        break

                if uncommitted_tx and report.journal_status != "CORRUPT":
                    report.journal_status = "DIRTY (Uncommitted Transactions)"

        return report
