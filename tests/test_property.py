"""
Property-based / Invariants randomized state testing against Python dict reference.
Uses standard random module with fixed deterministic seeds.
"""

import os
import random
import shutil
import tempfile
import unittest

from cacheforge.database import CacheForgeDB


class TestPropertyInvariants(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cacheforge_property_test_")
        self.db_path = os.path.join(self.temp_dir, "prop.cforge")
        self.db = CacheForgeDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_randomized_operations_against_dict_reference(self):
        seed = 424242
        num_operations = 5000
        random.seed(seed)

        reference_dict = {}
        key_space = [f"key_{i}" for i in range(100)]
        op_types = ["set", "get", "delete", "exists"]

        for step in range(num_operations):
            op = random.choice(op_types)
            key = random.choice(key_space)

            if op == "set":
                val = f"value_step_{step}_rnd_{random.randint(1, 10000)}"
                reference_dict[key] = val
                self.db.set(key, val)

            elif op == "get":
                ref_val = reference_dict.get(key)
                db_val = self.db.get_value(key)
                self.assertEqual(
                    db_val, ref_val,
                    f"Mismatch at step {step} for key '{key}': ref={ref_val!r}, db={db_val!r}"
                )

            elif op == "delete":
                ref_existed = key in reference_dict
                if ref_existed:
                    del reference_dict[key]
                db_deleted = self.db.delete(key)
                self.assertEqual(db_deleted, ref_existed)

            elif op == "exists":
                ref_exists = key in reference_dict
                db_exists = self.db.exists(key)
                self.assertEqual(db_exists, ref_exists)

        # Final state verification
        for k, v in reference_dict.items():
            self.assertEqual(self.db.get_value(k), v)

        # Verify compaction preserves invariants
        self.db.compact()
        for k, v in reference_dict.items():
            self.assertEqual(self.db.get_value(k), v)


if __name__ == "__main__":
    unittest.main()
