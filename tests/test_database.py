"""
Unit tests for core CacheForge database operations.
"""

import os
import shutil
import tempfile
import unittest

from cacheforge.database import CacheForgeDB
from cacheforge.errors import KeyNotFoundError


class TestCacheForgeDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cacheforge_test_db_")
        self.db_path = os.path.join(self.temp_dir, "test.cforge")
        self.db = CacheForgeDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_set_and_get_basic(self):
        self.assertTrue(self.db.set("user:1", "Riaz Aslam"))
        rec = self.db.get("user:1")
        self.assertIsNotNone(rec)
        self.assertEqual(rec.value_str, "Riaz Aslam")
        self.assertEqual(self.db.get_value("user:1"), "Riaz Aslam")

    def test_exists_and_delete(self):
        self.db.set("key1", "val1")
        self.assertTrue(self.db.exists("key1"))
        self.assertTrue(self.db.delete("key1"))
        self.assertFalse(self.db.exists("key1"))
        self.assertIsNone(self.db.get("key1"))
        self.assertFalse(self.db.delete("key1"))

    def test_missing_key(self):
        self.assertIsNone(self.db.get("nonexistent"))
        self.assertFalse(self.db.exists("nonexistent"))

    def test_overwrite_key(self):
        self.db.set("counter", "1")
        self.assertEqual(self.db.get_value("counter"), "1")
        self.db.set("counter", "2")
        self.assertEqual(self.db.get_value("counter"), "2")

    def test_empty_string_and_binary_values(self):
        self.db.set("empty", "")
        self.assertEqual(self.db.get_value("empty"), "")
        
        binary_data = b"\x00\x01\x02\xff\xfe"
        self.db.set("binary", binary_data)
        rec = self.db.get("binary")
        self.assertIsNotNone(rec)
        self.assertEqual(rec.value, binary_data)

    def test_unicode_and_large_values(self):
        unicode_str = "CacheForge 🔥 ⚡ 🚀 Multi-Language Data Store 零依赖"
        self.db.set("unicode_key", unicode_str)
        self.assertEqual(self.db.get_value("unicode_key"), unicode_str)

        large_val = "X" * (1024 * 1024)  # 1 MB
        self.db.set("large_key", large_val)
        self.assertEqual(self.db.get_value("large_key"), large_val)

    def test_persistence_across_reopen(self):
        self.db.set("perm_key", "Persisted Value")
        self.db.close()

        # Reopen existing database path
        db2 = CacheForgeDB(self.db_path)
        self.assertEqual(db2.get_value("perm_key"), "Persisted Value")
        db2.close()


if __name__ == "__main__":
    unittest.main()
