# CacheForge — Crash Recovery Engine

CacheForge implements Write-Ahead Logging (WAL) and automated crash recovery to ensure zero data loss for committed operations following process crashes, sudden power failures, or interrupted disk writes.

---

## 1. Crash Recovery Workflow

Upon database initialization (`CacheForgeDB(db_path, auto_recover=True)`) or explicit recovery command (`cacheforge recover <database>`):

```
                       +-------------------------+
                       |   Start Recovery Scan   |
                       +-------------------------+
                                    |
                                    v
                       +-------------------------+
                       | Scan data.log records   |
                       | Validate SHA-256 Hashes |
                       +-------------------------+
                                    |
                         (Corrupt Tail Detected?)
                         /                     \
                      Yes                       No
                      /                           \
        +----------------------------+  +----------------------------+
        | Truncate corrupt tail to   |  | Scan journal.log for       |
        | last valid record offset   |  | pending transaction logs   |
        +----------------------------+  +----------------------------+
                      \                           /
                       +-------------------------+
                                    |
                                    v
                     +-----------------------------+
                     | Replay committed WAL entries|
                     | Roll back uncommitted TXs   |
                     +-----------------------------+
                                    |
                                    v
                     +-----------------------------+
                     | Rebuild in-memory key index |
                     | & secondary search indexes  |
                     +-----------------------------+
```

---

## 2. Automated Recovery Test (`tools/crash_test.py`)

Run the deterministic crash recovery simulation:

```bash
python3 tools/crash_test.py
```

The script:
1. Writes 500 committed user records.
2. Injects a simulated process crash (uncommitted transaction in WAL + truncated garbage bytes at `data.log` tail).
3. Invokes `CacheForgeDB` recovery.
4. Verifies all 500 committed records survive, ghost transactions are rolled back, and SHA-256 integrity remains `VALID`.
