"""
Unit tests for SHA-256 Data Integrity Verification.
"""

import os
import shutil
import tempfile
import unittest

from cacheforge.database import CacheForgeDB
from cacheforge.integrity import IntegrityChecker


class TestIntegrity(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cacheforge_integrity_test_")
        self.db_path = os.path.join(self.temp_dir, "verify.cforge")
        self.db = CacheForgeDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_database_integrity(self):
        for i in range(50):
            self.db.set(f"key_{i}", f"val_{i}")
        
        report = self.db.verify()
        self.assertTrue(report.is_valid)
        self.assertEqual(report.records_scanned, 50)
        self.assertEqual(report.valid_records, 50)
        self.assertEqual(report.corrupt_records, 0)

    def test_corrupt_byte_injection_detection(self):
        self.db.set("target_key", "Target Value")
        self.db.close()

        data_log = os.path.join(self.db_path, "data.log")
        with open(data_log, "r+b") as f:
            f.seek(20)  # Flip bytes inside header/payload
            f.write(b"\xff\xff\xff\xff")
            f.flush()

        report = IntegrityChecker.verify_database(self.db_path)
        self.assertFalse(report.is_valid)
        self.assertGreater(report.corrupt_records, 0)
        self.assertEqual(report.index_status, "CORRUPT")


if __name__ == "__main__":
    unittest.main()
