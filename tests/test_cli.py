"""
Integration tests for CLI command execution.
"""

import json
import os
import shutil
import tempfile
import unittest

from cacheforge.cli import main


class TestCLI(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="cacheforge_cli_test_")
        self.db_path = os.path.join(self.temp_dir, "cli_demo.cforge")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_set_get_delete_workflow(self):
        ret_init = main(["init", self.db_path])
        self.assertEqual(ret_init, 0)

        ret_set = main(["set", self.db_path, "user:100", "Riaz Aslam", "--field", "role=student"])
        self.assertEqual(ret_set, 0)

        ret_get = main(["get", self.db_path, "user:100"])
        self.assertEqual(ret_get, 0)

        ret_query = main(["query", self.db_path, "--field", "role=student"])
        self.assertEqual(ret_query, 0)

        ret_stats = main(["stats", self.db_path, "--json"])
        self.assertEqual(ret_stats, 0)

        ret_verify = main(["verify", self.db_path])
        self.assertEqual(ret_verify, 0)

        ret_del = main(["delete", self.db_path, "user:100"])
        self.assertEqual(ret_del, 0)

        ret_get_missing = main(["get", self.db_path, "user:100"])
        self.assertEqual(ret_get_missing, 3)

    def test_cli_benchmark(self):
        ret = main(["benchmark", "--records", "500"])
        self.assertEqual(ret, 0)


if __name__ == "__main__":
    unittest.main()
