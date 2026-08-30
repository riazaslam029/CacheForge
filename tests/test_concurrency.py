"""
Unit tests for Concurrency and Thread Safety.
"""

import os
import shutil
import tempfile
import threading
import unittest

from cacheforge.database import CacheForgeDB


class TestConcurrency(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cacheforge_concurrent_test_")
        self.db_path = os.path.join(self.temp_dir, "concurrent.cforge")
        self.db = CacheForgeDB(self.db_path)

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_multithreaded_concurrent_writes(self):
        num_threads = 10
        ops_per_thread = 100
        errors = []

        def worker(thread_idx: int):
            try:
                for i in range(ops_per_thread):
                    key = f"t_{thread_idx}_k_{i}"
                    val = f"thread_{thread_idx}_val_{i}"
                    self.db.set(key, val, fields={"thread": thread_idx})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors encountered: {errors}")
        self.assertEqual(self.db.stats()["total_records"], num_threads * ops_per_thread)

    def test_concurrent_readers_writers(self):
        errors = []
        stop_event = threading.Event()

        def writer():
            idx = 0
            while not stop_event.is_set():
                try:
                    self.db.set("shared_key", f"val_{idx}")
                    idx += 1
                except Exception as e:
                    errors.append(e)

        def reader():
            while not stop_event.is_set():
                try:
                    _ = self.db.get("shared_key")
                except Exception as e:
                    errors.append(e)

        w_thread = threading.Thread(target=writer)
        r_threads = [threading.Thread(target=reader) for _ in range(5)]

        w_thread.start()
        for r in r_threads:
            r.start()

        import time
        time.sleep(0.5)
        stop_event.set()

        w_thread.join()
        for r in r_threads:
            r.join()

        self.assertEqual(len(errors), 0)


if __name__ == "__main__":
    unittest.main()
