"""
Unit tests for Log Compaction.
"""

import os
import shutil
import tempfile
import time
import unittest

from cacheforge.database import CacheForgeDB


class TestCompaction(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cacheforge_compact_test_")
        self.db_path = os.path.join(self.temp_dir, "compact.cforge")
        self.db = CacheForgeDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_compaction_reclaims_space(self):
        # Create many overwritten and deleted entries
        for i in range(100):
            self.db.set("overwrite_key", f"Version {i}")
        
        for i in range(100):
            self.db.set(f"temp_key_{i}", f"val_{i}")
            self.db.delete(f"temp_key_{i}")

        self.db.set("keep_key", "Permanent Value")
        self.db.set("expired_key", "Expired Value", ttl=0.05)
        time.sleep(0.1)

        data_size_before = os.path.getsize(self.db.data_log_path)
        report = self.db.compact()

        self.assertGreater(report.bytes_saved, 0)
        self.assertEqual(report.retained_keys, 2)  # overwrite_key and keep_key
        self.assertEqual(self.db.get_value("overwrite_key"), "Version 99")
        self.assertEqual(self.db.get_value("keep_key"), "Permanent Value")
        self.assertFalse(self.db.exists("temp_key_0"))
        self.assertFalse(self.db.exists("expired_key"))

    def test_database_state_equality_after_compaction(self):
        self.db.set("k1", "v1")
        self.db.set("k2", "v2")
        self.db.set("k3", "v3")
        self.db.delete("k2")

        self.db.compact()

        self.assertEqual(self.db.get_value("k1"), "v1")
        self.assertFalse(self.db.exists("k2"))
        self.assertEqual(self.db.get_value("k3"), "v3")


if __name__ == "__main__":
    unittest.main()
