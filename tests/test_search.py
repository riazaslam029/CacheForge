"""
Unit tests for Full-Text Inverted Index Search Engine.
"""

import os
import shutil
import tempfile
import unittest

from cacheforge.database import CacheForgeDB


class TestFullTextSearch(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cacheforge_search_test_")
        self.db_path = os.path.join(self.temp_dir, "search.cforge")
        self.db = CacheForgeDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_basic_search(self):
        self.db.set("doc:1", "CacheForge is a high performance zero-dependency embedded database")
        self.db.set("doc:2", "Python standard library provides struct mmap and hashlib")
        self.db.set("doc:3", "Embedded key-value storage engines require write-ahead logging")

        results = self.db.search("embedded storage database")
        self.assertEqual(len(results), 2)
        keys = [rec.key for rec, score in results]
        self.assertIn("doc:1", keys)
        self.assertIn("doc:3", keys)

    def test_search_score_ranking(self):
        self.db.set("doc:a", "python python python database engine")
        self.db.set("doc:b", "python database")

        results = self.db.search("python")
        self.assertEqual(len(results), 2)
        # doc:a should have higher TF score than doc:b
        self.assertEqual(results[0][0].key, "doc:a")

    def test_search_ignores_deleted_and_expired(self):
        self.db.set("doc:del", "secret search token payload")
        self.db.set("doc:exp", "secret search token payload", ttl=0.05)
        
        self.db.delete("doc:del")
        import time
        time.sleep(0.1)

        results = self.db.search("secret search token")
        self.assertEqual(len(results), 0)


if __name__ == "__main__":
    unittest.main()
