# CacheForge

**A zero-dependency embedded storage engine with persistence, indexing, TTL, search, journaling, and crash recovery.**

Built for **Zero Dependency Hackathon — Track D: Data & Storage**.

---

## ⚡ What is CacheForge?

CacheForge is a feature-rich, durability-focused local embedded storage engine implemented **100% using Python's standard library**. It provides crash recovery, WAL journaling, index querying, full-text search, TTL expiration, and data integrity verification without requiring any third-party `pip` packages.

### Why Zero Dependencies Matter
Modern software stacks often pull in hundreds of external dependencies for basic tasks like binary packing (`msgpack`), file locking (`filelock`), CLI interfaces (`click`/`rich`), or cryptographic hashes (`cryptography`). CacheForge demonstrates that by using operating system primitives and Python standard library modules (`struct`, `fcntl`, `hashlib`, `argparse`, `os.fsync`), you can build a resilient, embedded storage engine with zero external supply chain risk.

---

## 🌟 Key Features

* **Persistent Key-Value Store**: Binary append-only data storage model with deterministic serialization.
* **Write-Ahead Logging (WAL)**: fsync-backed durable writes with transaction framing and crash recovery.
* **Automated Crash Recovery**: Recovers committed state, rolls back incomplete writes, and truncates corrupt log tails upon startup (`cacheforge recover`).
* **SHA-256 Data Integrity**: Cryptographic per-record checksum verification detecting bit rot and corrupt headers (`cacheforge verify`).
* **Secondary Field Indexing**: Fast query lookups on structured metadata fields (`cacheforge query --field role=student`).
* **Full-Text Inverted Search**: Tokenization, term-frequency inverted index maps, and TF-IDF relevance scoring (`cacheforge search`).
* **TTL & Key Expiration**: Microsecond precision expiration with lazy checks, eager sweeps, and persistent TTLs (`cacheforge set --ttl 3600`).
* **Atomic Compaction**: Purges obsolete versions, deleted tombstones, and expired keys with atomic directory swaps (`cacheforge compact`).
* **Concurrency Controls**: Process file locking (`fcntl.flock`) and thread-safe reentrant locks (`threading.RLock`).
* **CLI & Machine-Readable Output**: Full command-line interface with `--json` support for scriptable workflows.
* **Reproducible Benchmarks**: In-process benchmark suite measuring throughput (ops/sec) and search/recovery latencies (`cacheforge benchmark`).

---

## 🏗️ Architecture

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

## 🚀 Quick Start

### 1. Installation
Clone the repository. No installation or `pip install` required!

```bash
git clone https://github.com/riazaslam029/CacheForge.git
cd CacheForge
```

### 2. Basic CLI Commands

```bash
# Initialize a new database
python3 cacheforge.py init mydb.cforge

# Set key-value records with fields and TTL
python3 cacheforge.py set mydb.cforge user:1 "Riaz Aslam" --field role=student --field city=Lahore
python3 cacheforge.py set mydb.cforge session:123 "Active Token" --ttl 3600

# Get record
python3 cacheforge.py get mydb.cforge user:1

# Query secondary field index
python3 cacheforge.py query mydb.cforge --field role=student

# Full-text inverted search
python3 cacheforge.py search mydb.cforge "Riaz"

# Verify SHA-256 data integrity
python3 cacheforge.py verify mydb.cforge

# Display database statistics (JSON format)
python3 cacheforge.py stats mydb.cforge --json
```

---

## 📊 Benchmarks

Run the reproducible benchmark suite locally with:

```bash
python3 cacheforge.py benchmark --records 10000
```

Performance metrics depend on hardware, Python runtime version, storage device I/O capabilities, database size, and workload.

---

## 🧪 Testing & Verification

### Run Complete Unit Test Suite
```bash
python3 -m unittest discover -v -s tests
```

### Run Property-Based Invariant Tests
```bash
python3 -m unittest tests/test_property.py
```

### Run Crash Recovery Simulation
```bash
python3 tools/crash_test.py
```

### Run Zero-Dependency AST Auditor
```bash
python3 tools/check_dependencies.py
```

---

## 📽️ Judge Demo

Execute the automated end-to-end judge demonstration:

```bash
./examples/demo.sh
```

---

## 📋 Standard Library Replacement Summary

| Feature | Standard Library Component | Replaced Third-Party Package |
| :--- | :--- | :--- |
| CLI Framework | `argparse` | `click` / `typer` / `rich` |
| Binary Encoding | `struct` | `protobuf` / `msgpack` |
| Integrity Hashing | `hashlib` (SHA-256) | `cryptography` / `crc32c` |
| Durability | `os.fsync` + `pathlib` | `redis-py` / `diskcache` |
| File Locking | `fcntl.flock` + `threading` | `filelock` / `portalocker` |
| Full-Text Search | `re` + `math` (TF-IDF) | `elasticsearch` / `whoosh` |
| Property Testing | `random` (fixed seeds) | `hypothesis` |

*(See [STDLIB.md](STDLIB.md) for full audit breakdown).*

---

## ⚠️ Known Limitations & Design Decisions

1. **Single-Node Architecture**: Designed for local embedded application storage; not a distributed consensus cluster.
2. **Platform Locking**: Process locking relies on POSIX `fcntl.flock` (with lockfile fallback for Windows).
3. **In-Memory Key Index**: Primary key lookup index is stored in RAM and rebuilt on startup for maximum speed.

