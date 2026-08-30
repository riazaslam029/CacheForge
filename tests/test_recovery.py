"""
Unit tests for Crash Recovery and Log Replay.
"""

import os
import shutil
import tempfile
import unittest

from cacheforge.database import CacheForgeDB
from cacheforge.recovery import RecoveryEngine
from cacheforge.records import Record, RecordType


class TestRecovery(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cacheforge_recovery_test_")
        self.db_path = os.path.join(self.temp_dir, "recover.cforge")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_uncommitted_journal_rollback(self):
        db = CacheForgeDB(self.db_path, auto_recover=False)
        db.set("committed_1", "val_1")
        db.close()

        # Inject uncommitted transaction into journal.log
        journal_path = os.path.join(self.db_path, "journal.log")
        tx_start = Record(key="__tx_start__", value=b"", record_type=RecordType.TX_START, sequence=100)
        uncommitted = Record(key="uncommitted_key", value=b"ghost", record_type=RecordType.SET, sequence=100)
        
        with open(journal_path, "ab") as f:
            f.write(tx_start.encode())
            f.write(uncommitted.encode())
            f.flush()

        db_rec = CacheForgeDB(self.db_path, auto_recover=True)
        report = db_rec.last_recovery_report
        self.assertIsNotNone(report)
        self.assertEqual(report.rolled_back_transactions, 1)

        self.assertTrue(db_rec.exists("committed_1"))
        self.assertFalse(db_rec.exists("uncommitted_key"))
        db_rec.close()

    def test_corrupted_data_tail_truncation(self):
        db = CacheForgeDB(self.db_path, auto_recover=False)
        db.set("k1", "v1")
        db.close()

        # Append corrupted bytes to data.log
        data_path = os.path.join(self.db_path, "data.log")
        with open(data_path, "ab") as f:
            f.write(b"CORRUPTED_HEADER_GARBAGE_BYTES_12345")
            f.flush()

        db_rec = CacheForgeDB(self.db_path, auto_recover=True)
        self.assertEqual(db_rec.get_value("k1"), "v1")
        integrity = db_rec.verify()
        self.assertTrue(integrity.is_valid)
        db_rec.close()


if __name__ == "__main__":
    unittest.main()
