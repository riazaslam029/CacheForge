# CacheForge — Standard Library Replacement Log (STDLIB.md)

CacheForge achieves 100% zero third-party runtime dependencies by leveraging Python's rich standard library modules. This document outlines 10+ standard library components that replace external packages commonly used in storage engines and developer tools.

---

| Common External Package | Standard Library Replacement | CacheForge Functionality | Tradeoff / Rationale |
| :--- | :--- | :--- | :--- |
| **`click` / `typer` / `rich`** | `argparse` | CLI command parsing, options, help formatting, and subcommands. | Zero external setup; native to Python 3. Standard output formatting is kept clean and readable without Unicode styling issues. |
| **`protobuf` / `msgpack` / `pickle`** | `struct` | Binary serialization of records, fixed 70-byte headers, network byte ordering (`>`). | Explicit binary layout; avoids `pickle` security execution vulnerabilities; zero third-party build toolchain requirements. |
| **`cryptography` / `crc32c`** | `hashlib` (SHA-256) | Per-record SHA-256 checksum generation and data integrity verification. | SHA-256 provides strong 256-bit cryptographic verification against corruption without needing external native C extensions. |
| **`redis-py` / `diskcache`** | `pathlib` + `os` + `io` | File descriptor management, atomic directory replaces (`os.replace`), and `os.fsync`. | Direct interaction with operating system filesystem primitives guarantees true crash durability. |
| **`filelock` / `portalocker`** | `threading` + `fcntl` | Multi-thread `RLock` synchronization and multi-process OS `fcntl.flock` file locking. | Leverages POSIX OS process kernel locks for mutual exclusion without external locking daemons. |
| **`pydantic` / `marshmallow`** | `dataclasses` + `json` | Structured record metadata validation and secondary field index serialization. | Standard Python dataclasses provide strict typing and clean schema definitions out of the box. |
| **`nltk` / `whoosh` / `elasticsearch`** | `re` + `math` | RegEx tokenization, stop-word filtering, term-frequency inverted indexing, and TF-IDF scoring. | Custom lightweight inverted index delivers sub-millisecond search latencies without heavyweight search engines. |
| **`hypothesis`** | `random` | Property-based randomized state testing comparing CacheForge against `dict` reference models. | Fixed deterministic seeds ensure 100% reproducible test runs in clean Python environments. |
| **`pytest`** | `unittest` | Complete test suite execution (`python3 -m unittest discover -v`). | Built into standard Python installation; zero external runner or plugin setup needed. |
| **`pytest-benchmark`** | `time` + `statistics` | Microsecond-precision benchmarking and percentile (p50, p95) calculation. | In-process high-resolution `time.perf_counter()` benchmarking without external benchmark frameworks. |
