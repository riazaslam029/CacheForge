"""
Unit tests for Time-To-Live (TTL) key expiration.
"""

import os
import shutil
import tempfile
import time
import unittest

from cacheforge.database import CacheForgeDB
from cacheforge.errors import KeyNotFoundError


class TestTTL(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cacheforge_ttl_test_")
        self.db_path = os.path.join(self.temp_dir, "ttl.cforge")
        self.db = CacheForgeDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_ttl_set_and_get(self):
        self.db.set("session:123", "User Session Data", ttl=10.0)
        self.assertEqual(self.db.get_value("session:123"), "User Session Data")
        rem_ttl = self.db.ttl("session:123")
        self.assertGreater(rem_ttl, 0.0)
        self.assertLessEqual(rem_ttl, 10.0)

    def test_lazy_expiration(self):
        self.db.set("short_lived", "Temp Value", ttl=0.1)  # 100ms
        self.assertEqual(self.db.get_value("short_lived"), "Temp Value")
        
        time.sleep(0.15)  # Wait for expiration
        
        self.assertIsNone(self.db.get("short_lived"))
        self.assertFalse(self.db.exists("short_lived"))
        with self.assertRaises(KeyNotFoundError):
            self.db.ttl("short_lived")

    def test_persist_and_expire(self):
        self.db.set("temp_key", "Temp", ttl=5.0)
        self.assertGreater(self.db.ttl("temp_key"), 0)

        self.db.persist("temp_key")
        self.assertEqual(self.db.ttl("temp_key"), -1.0)

        self.db.expire("temp_key", 20.0)
        self.assertGreater(self.db.ttl("temp_key"), 0)

    def test_eager_cleanup(self):
        self.db.set("k1", "v1", ttl=0.05)
        self.db.set("k2", "v2", ttl=100.0)
        time.sleep(0.1)

        purged_count = self.db.cleanup()
        self.assertEqual(purged_count, 1)
        self.assertFalse(self.db.exists("k1"))
        self.assertTrue(self.db.exists("k2"))


if __name__ == "__main__":
    unittest.main()
