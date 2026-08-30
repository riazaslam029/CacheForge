#!/usr/bin/env python3
"""
Deterministic Crash Recovery Test Utility.
Simulates mid-transaction process crashes and file truncation, verifying crash safety and WAL replay.
"""

import os
import shutil
import sys
import tempfile

# Ensure project root is in sys.path when executed directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cacheforge.database import CacheForgeDB
from cacheforge.records import Record, RecordType


def run_crash_test() -> bool:
    print("Executing Deterministic Crash Recovery Test...")
    test_dir = tempfile.mkdtemp(prefix="cacheforge_crash_test_")

    try:
        db_path = os.path.join(test_dir, "crash_demo.cforge")

        # Step 1: Write initial batch of committed records
        print("  1. Writing 500 committed records...")
        db = CacheForgeDB(db_path, auto_recover=False)
        for i in range(500):
            db.set(f"committed_user_{i}", f"User Data {i}", fields={"status": "verified", "id": i})
        db.close()

        # Verify size before simulated crash
        data_log_path = os.path.join(db_path, "data.log")
        journal_log_path = os.path.join(db_path, "journal.log")
        data_size_before = os.path.getsize(data_log_path)

        # Step 2: Inject simulated process crash (incomplete transaction in WAL + truncated record in data.log)
        print("  2. Injecting simulated process crash (uncommitted WAL transaction + corrupted log tail)...")
        seq = 501
        uncommitted_record = Record(
            key="uncommitted_key_999",
            value=b"Ghost payload that was never committed",
            record_type=RecordType.SET,
            sequence=seq
        )

        # Write TX_START + Record into journal WITHOUT writing TX_COMMIT
        tx_start = Record(key="__tx_start__", value=b"", record_type=RecordType.TX_START, sequence=seq)
        with open(journal_log_path, "ab") as f:
            f.write(tx_start.encode())
            f.write(uncommitted_record.encode())
            f.flush()
            os.fsync(f.fileno())

        # Append partial/corrupted bytes to data.log tail (simulating power failure mid-record write)
        with open(data_log_path, "ab") as f:
            f.write(b"CFRG\x01\x01" + b"\x00" * 20)  # Corrupted partial header
            f.flush()
            os.fsync(f.fileno())

        # Step 3: Perform recovery
        print("  3. Starting CacheForge database recovery engine...")
        db_recovered = CacheForgeDB(db_path, auto_recover=True)
        report = db_recovered.last_recovery_report

        print(f"     Recovery Status: {report.status}")
        print(f"     Rolled Back Transactions: {report.rolled_back_transactions}")

        # Step 4: Assert invariants
        print("  4. Validating recovered database state...")

        # Assert uncommitted record was rolled back
        if db_recovered.exists("uncommitted_key_999"):
            print("❌ FAIL: Uncommitted record was found after recovery!")
            return False

        # Assert all 500 committed records are intact
        for i in range(500):
            val = db_recovered.get_value(f"committed_user_{i}")
            if val != f"User Data {i}":
                print(f"❌ FAIL: Committed key 'committed_user_{i}' missing or corrupt: got {val!r}")
                return False

        # Assert integrity checker reports VALID
        integrity = db_recovered.verify()
        if not integrity.is_valid:
            print("❌ FAIL: Integrity verification failed post-recovery!")
            return False

        # Assert database accepts new writes cleanly post-recovery
        db_recovered.set("post_recovery_key", "Recovery Success!")
        if db_recovered.get_value("post_recovery_key") != "Recovery Success!":
            print("❌ FAIL: Could not set new record post-recovery!")
            return False

        db_recovered.close()
        print("✓ Crash Recovery Test PASSED: All 500 committed records recovered, ghost transaction rolled back, integrity VALID!")
        return True

    finally:
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    success = run_crash_test()
    sys.exit(0 if success else 1)
