"""
Crash Recovery Engine.
Replays committed WAL transactions, discards uncommitted/partial writes, rebuilds indexes, and restores state.
"""

from dataclasses import dataclass, field
import os
from typing import List, Dict, Tuple, Optional

from cacheforge.records import Record, RecordType
from cacheforge.errors import InvalidRecordError, CorruptionError, RecoveryError


@dataclass
class RecoveryReport:
    replayed_records: int = 0
    rolled_back_transactions: int = 0
    valid_data_records: int = 0
    status: str = "CLEAN"
    details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, object]:
        return {
            "replayed_records": self.replayed_records,
            "rolled_back_transactions": self.rolled_back_transactions,
            "valid_data_records": self.valid_data_records,
            "status": self.status,
            "details": self.details
        }

    def format_text(self) -> str:
        lines = [
            "CacheForge Crash Recovery Report",
            "================================",
            f"Recovery Status:            {self.status}",
            f"Replayed Journal Records:   {self.replayed_records}",
            f"Rolled Back Transactions:   {self.rolled_back_transactions}",
            f"Valid Active Data Records:  {self.valid_data_records}"
        ]
        if self.details:
            lines.append("\nRecovery Details:")
            for d in self.details:
                lines.append(f"  - {d}")
        return "\n".join(lines)


class RecoveryEngine:
    """
    Scans data.log and journal.log, handles process interruption recovery.
    """

    @classmethod
    def recover_database(cls, db_dir: str) -> Tuple[RecoveryReport, Dict[str, Record], List[Record]]:
        """
        Scans logs, purges corrupt/incomplete records, replays valid operations.
        Returns (RecoveryReport, active_records_map, all_valid_records_list).
        """
        report = RecoveryReport()
        data_log_path = os.path.join(db_dir, "data.log")
        journal_log_path = os.path.join(db_dir, "journal.log")

        valid_records: List[Record] = []
        active_records: Dict[str, Record] = {}
        last_valid_data_offset = 0

        # 1. Read existing valid records from data.log up to any corrupted tail
        if os.path.exists(data_log_path):
            with open(data_log_path, "rb") as f:
                offset = 0
                while True:
                    f.seek(offset)
                    try:
                        rec, bytes_read = Record.read_from_stream(f)
                        if rec is None:
                            break
                        valid_records.append(rec)
                        if rec.record_type == RecordType.SET:
                            active_records[rec.key] = rec
                        elif rec.record_type == RecordType.DELETE:
                            active_records.pop(rec.key, None)
                        last_valid_data_offset = offset + bytes_read
                        offset += bytes_read
                    except (InvalidRecordError, CorruptionError) as err:
                        report.status = "RECOVERED"
                        report.details.append(f"Truncated corrupt tail from data.log at offset {offset}: {err}")
                        break
                    except Exception as e:
                        report.status = "RECOVERED"
                        report.details.append(f"Truncated data.log at offset {offset}: {e}")
                        break

            # Truncate corrupt tail if data.log was larger than last valid record offset
            if os.path.getsize(data_log_path) > last_valid_data_offset:
                with open(data_log_path, "a+b") as f:
                    f.truncate(last_valid_data_offset)
                    f.flush()
                    os.fsync(f.fileno())

        # 2. Replay Journal (journal.log)
        journal_records_to_append: List[Record] = []
        if os.path.exists(journal_log_path) and os.path.getsize(journal_log_path) > 0:
            tx_buffer: List[Record] = []
            in_tx = False

            with open(journal_log_path, "rb") as f:
                offset = 0
                while True:
                    f.seek(offset)
                    try:
                        rec, bytes_read = Record.read_from_stream(f)
                        if rec is None:
                            break

                        if rec.record_type == RecordType.TX_START:
                            in_tx = True
                            tx_buffer = []
                        elif rec.record_type == RecordType.TX_COMMIT:
                            if in_tx:
                                for committed_rec in tx_buffer:
                                    journal_records_to_append.append(committed_rec)
                                    report.replayed_records += 1
                                in_tx = False
                                tx_buffer = []
                        elif rec.record_type == RecordType.TX_ABORT:
                            in_tx = False
                            tx_buffer = []
                            report.rolled_back_transactions += 1
                        else:
                            if in_tx:
                                tx_buffer.append(rec)
                            else:
                                # Standalone committed operation in journal
                                journal_records_to_append.append(rec)
                                report.replayed_records += 1

                        offset += bytes_read
                    except Exception as err:
                        if in_tx:
                            report.rolled_back_transactions += 1
                            report.details.append(f"Rolled back incomplete transaction due to journal corruption: {err}")
                        break

            if in_tx:
                report.rolled_back_transactions += 1
                report.details.append("Rolled back uncommitted transaction at end of journal log")

            # Append replayed journal records into data.log
            if journal_records_to_append:
                report.status = "RECOVERED"
                with open(data_log_path, "a+b") as f:
                    for rec in journal_records_to_append:
                        f.write(rec.encode())
                        valid_records.append(rec)
                        if rec.record_type == RecordType.SET:
                            active_records[rec.key] = rec
                        elif rec.record_type == RecordType.DELETE:
                            active_records.pop(rec.key, None)
                    f.flush()
                    os.fsync(f.fileno())

            # Clear journal.log after successful recovery replay
            with open(journal_log_path, "wb") as f:
                f.truncate(0)
                f.flush()
                os.fsync(f.fileno())

        report.valid_data_records = len(active_records)
        return report, active_records, valid_records
