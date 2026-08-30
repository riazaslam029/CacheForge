# CacheForge — System Architecture

CacheForge is an embedded persistent key-value data engine implemented strictly using Python's standard library. It provides durability, crash recovery, secondary field indexing, full-text inverted search, TTL key expiration, atomic compaction, and multi-thread/multi-process concurrency controls.

---

## 1. High-Level Engine Overview

```
+-----------------------------------------------------------------------+
|                              CacheForge CLI                           |
|                       (argparse / JSON output API)                    |
+-----------------------------------------------------------------------+
                                   |
                                   v
+-----------------------------------------------------------------------+
|                             CacheForgeDB                              |
|                   (Core Database Coordinator Engine)                  |
+-----------------------------------------------------------------------+
    |               |               |               |               |
    v               v               v               v               v
+-------+       +-------+       +-------+       +-------+       +-------+
| Lock  |       |  WAL  |       | In-Mem|       |Field  |       | Full- |
| Engine|       |Journal|       | Key   |       |Index  |       | Text  |
|(fcntl)|       |(fsync)|       | Index |       | (Map) |       | Search|
+-------+       +-------+       +-------+       +-------+       +-------+
    |               |               |               |               |
    v               v               v               v               v
+-----------------------------------------------------------------------+
|                      Persistent File System Storage                   |
| (data.log | journal.log | manifest | index/ | snapshots/ | lock)      |
+-----------------------------------------------------------------------+
```

---

## 2. Directory Layout & Storage Components

A CacheForge database instance lives in a single directory (e.g. `mydb.cforge/`):

* **`data.log`**: Binary append-only record file storing sequential data records.
* **`journal.log`**: Write-Ahead Log (WAL) file storing atomic transaction logs before data log append.
* **`manifest`**: JSON metadata file tracking monotonic sequence counters, database version, and format parameters.
* **`index/`**: Directory storing serialized snapshots of field indexes (`fields.idx`) and full-text inverted search indexes (`search.idx`).
* **`snapshots/`**: Point-in-time point recovery snapshots.
* **`lock`**: Advisory OS process file lock (`fcntl.flock` / lockfile fallback).

---

## 3. Component Breakdown

### A. Record Serialization (`records.py`)
Encodes keys, values, metadata, and fields into binary payloads using Python's `struct` module (`>4sBBQQQIII32s`) with fixed 70-byte headers and SHA-256 payload checksum verification.

### B. Write-Ahead Logging & Durability (`journal.py`)
All mutating operations (set, delete) are appended to `journal.log` framed by `TX_START` and `TX_COMMIT` markers and synchronized to hardware using `os.fsync()`.

### C. Crash Recovery (`recovery.py`)
Scans `journal.log` and `data.log` upon database startup. Replays committed transactions, discards incomplete/corrupted transactions, truncates corrupt log tails, and rebuilds in-memory indexes.

### D. Data Integrity Verification (`integrity.py`)
Scans raw binary log files and computes SHA-256 hashes over record headers and payloads to detect bit rot, partial writes, or header corruption.

### E. Secondary Field Indexing (`index.py`)
Maps field metadata (`field_name: field_value -> set(record_keys)`) to enable fast multi-field query lookups (`cacheforge query --field role=student`).

### F. Full-Text Inverted Search (`search.py`)
Tokenizes text content, maintains term frequency inverted index maps, and computes TF-IDF document relevance scores (`cacheforge search`).

### G. Time-To-Live (TTL) & Expiration (`ttl.py`)
Calculates microsecond expiration epoch timestamps. Supports lazy expiration checks during reads, eager cleanup sweeps, and compaction purges.

### H. Compaction (`compaction.py`)
Scans the database, discards superseded record versions, deleted tombstones, and expired keys. Atomically swaps the old log file with a newly compacted log file using `os.replace`.

### I. Thread & Process Concurrency (`locking.py`)
Guarantees thread-safety via `threading.RLock` and process isolation via `fcntl.flock` (or lockfile fallback).
