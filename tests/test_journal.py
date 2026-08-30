"""
Unit tests for Write-Ahead Logging (WAL) and Journaling.
"""

import os
import shutil
import tempfile
import unittest

from cacheforge.journal import Journal
from cacheforge.records import Record, RecordType


class TestJournal(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cacheforge_journal_test_")
        self.journal_path = os.path.join(self.temp_dir, "journal.log")
        self.journal = Journal(self.journal_path)

    def tearDown(self):
        self.journal.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_write_and_read_single_record(self):
        rec = Record(key="j_key", value=b"j_val", sequence=1)
        bytes_written = self.journal.write_record(rec, fsync=True)
        self.assertGreater(bytes_written, 0)

        entries = self.journal.read_all_records()
        self.assertEqual(len(entries), 1)
        read_rec, offset, length = entries[0]
        self.assertEqual(read_rec.key, "j_key")
        self.assertEqual(read_rec.value, b"j_val")

    def test_append_transaction(self):
        rec1 = Record(key="k1", value=b"v1", sequence=10)
        rec2 = Record(key="k2", value=b"v2", sequence=10)
        
        self.journal.append_transaction([rec1, rec2], fsync=True)

        entries = self.journal.read_all_records()
        self.assertEqual(len(entries), 4)  # TX_START, rec1, rec2, TX_COMMIT
        self.assertEqual(entries[0][0].record_type, RecordType.TX_START)
        self.assertEqual(entries[3][0].record_type, RecordType.TX_COMMIT)

    def test_truncate_journal(self):
        rec = Record(key="k_trunc", value=b"val", sequence=1)
        self.journal.write_record(rec)
        self.assertGreater(os.path.getsize(self.journal_path), 0)

        self.journal.truncate()
        self.assertEqual(os.path.getsize(self.journal_path), 0)
        entries = self.journal.read_all_records()
        self.assertEqual(len(entries), 0)


if __name__ == "__main__":
    unittest.main()
