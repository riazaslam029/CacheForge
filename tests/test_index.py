"""
Unit tests for Secondary Field Indexing.
"""

import os
import shutil
import tempfile
import unittest

from cacheforge.database import CacheForgeDB


class TestSecondaryIndex(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cacheforge_index_test_")
        self.db_path = os.path.join(self.temp_dir, "index.cforge")
        self.db = CacheForgeDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_single_field_query(self):
        self.db.set("user:1", "Riaz", fields={"role": "student", "city": "Lahore"})
        self.db.set("user:2", "Ali", fields={"role": "student", "city": "Karachi"})
        self.db.set("user:3", "Sara", fields={"role": "engineer", "city": "Lahore"})

        students = self.db.query({"role": "student"})
        self.assertEqual(len(students), 2)
        student_keys = [r.key for r in students]
        self.assertIn("user:1", student_keys)
        self.assertIn("user:2", student_keys)

    def test_compound_field_query(self):
        self.db.set("u1", "Riaz", fields={"role": "student", "city": "Lahore"})
        self.db.set("u2", "Ali", fields={"role": "student", "city": "Karachi"})
        self.db.set("u3", "Sara", fields={"role": "student", "city": "Lahore"})

        results = self.db.query({"role": "student", "city": "Lahore"})
        self.assertEqual(len(results), 2)
        res_keys = [r.key for r in results]
        self.assertIn("u1", res_keys)
        self.assertIn("u3", res_keys)

    def test_index_update_and_deletion(self):
        self.db.set("u1", "Riaz", fields={"role": "student"})
        self.assertEqual(len(self.db.query({"role": "student"})), 1)

        # Update fields
        self.db.set("u1", "Riaz", fields={"role": "alumni"})
        self.assertEqual(len(self.db.query({"role": "student"})), 0)
        self.assertEqual(len(self.db.query({"role": "alumni"})), 1)

        # Delete key
        self.db.delete("u1")
        self.assertEqual(len(self.db.query({"role": "alumni"})), 0)


if __name__ == "__main__":
    unittest.main()
