# CacheForge — Performance Benchmarks

CacheForge includes a reproducible benchmarking engine (`cacheforge benchmark`) measuring throughput and latency percentiles.

---

## 1. Reproducible Benchmark Execution

To execute the benchmark suite:

```bash
python3 cacheforge.py benchmark --records 10000
```

Or generate machine-readable JSON results:

```bash
python3 cacheforge.py benchmark --records 10000 --json
```

---

## 2. Benchmark Output Format Example

```
CacheForge Benchmark Results
============================
Dataset Size:           10,000 records
Sequential Writes:      35,420 ops/sec
Random Reads:           92,150 ops/sec
Deletes Throughput:     45,100 ops/sec

Full-Text Search Latency:
  p50 (Median):         1.820 ms
  p95 (95th Percentile): 4.150 ms

Database Startup/Recovery: 12.40 ms
Final Database Size:       1.45 MB
```

---

## 3. Methodology & Hardware Notes

* **Write Throughput**: Sequential `set` operations with Write-Ahead Logging.
* **Random Read Throughput**: In-memory binary key index lookups with lazy TTL verification.
* **Search Latency**: TF-IDF inverted index term evaluation across multi-word queries.
* **Recovery Speed**: Cold startup log scan, SHA-256 audit, and secondary index construction time.

*Note: Measured benchmark throughput and latency vary depending on the host hardware, storage device I/O, Python version, and system load.*

