"""
CacheForge Reproducible Benchmarking Engine.
Measures write, read, delete throughput and search/recovery latency percentiles.
"""

from dataclasses import dataclass, field
import json
import os
import random
import tempfile
import time
from typing import Dict, List, Any

from cacheforge.database import CacheForgeDB


@dataclass
class BenchmarkResult:
    dataset_records: int
    write_ops_per_sec: float
    read_ops_per_sec: float
    delete_ops_per_sec: float
    search_latency_p50_ms: float
    search_latency_p95_ms: float
    recovery_time_ms: float
    db_size_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dataset_records": self.dataset_records,
            "sequential_writes_ops_sec": round(self.write_ops_per_sec, 2),
            "random_reads_ops_sec": round(self.read_ops_per_sec, 2),
            "deletes_ops_sec": round(self.delete_ops_per_sec, 2),
            "search_latency_p50_ms": round(self.search_latency_p50_ms, 3),
            "search_latency_p95_ms": round(self.search_latency_p95_ms, 3),
            "recovery_time_ms": round(self.recovery_time_ms, 2),
            "db_size_bytes": self.db_size_bytes
        }

    def format_text(self) -> str:
        lines = [
            "CacheForge Benchmark Results",
            "============================",
            f"Dataset Size:           {self.dataset_records:,} records",
            f"Sequential Writes:      {self.write_ops_per_sec:,.0f} ops/sec",
            f"Random Reads:           {self.read_ops_per_sec:,.0f} ops/sec",
            f"Deletes Throughput:     {self.delete_ops_per_sec:,.0f} ops/sec",
            "",
            "Full-Text Search Latency:",
            f"  p50 (Median):         {self.search_latency_p50_ms:.3f} ms",
            f"  p95 (95th Percentile): {self.search_latency_p95_ms:.3f} ms",
            "",
            f"Database Startup/Recovery: {self.recovery_time_ms:.2f} ms",
            f"Final Database Size:       {self.db_size_bytes / (1024 * 1024):.2f} MB"
        ]
        return "\n".join(lines)


class BenchmarkRunner:
    """
    Executes benchmark suites against temporary CacheForge databases.
    """

    @classmethod
    def run_benchmark(cls, num_records: int = 10000, seed: int = 42) -> BenchmarkResult:
        random.seed(seed)
        sample_words = [
            "distributed", "storage", "engine", "python", "database", "journal", "recovery",
            "checksum", "transaction", "compaction", "indexing", "concurrency", "performance"
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "benchmark.cforge")
            db = CacheForgeDB(db_path, auto_recover=False)

            # 1. Sequential Write Benchmark
            keys = [f"bench_key_{i}" for i in range(num_records)]
            payloads = []
            for i in range(num_records):
                text_val = " ".join(random.sample(sample_words, k=4)) + f" record_{i}"
                field_val = {"role": "bench", "id": i % 100}
                payloads.append((text_val, field_val))

            start_write = time.perf_counter()
            for i in range(num_records):
                db.set(keys[i], payloads[i][0], fields=payloads[i][1])
            write_time = time.perf_counter() - start_write
            write_ops_sec = num_records / write_time if write_time > 0 else 0.0

            # 2. Random Read Benchmark
            num_reads = min(num_records, 10000)
            read_keys = [random.choice(keys) for _ in range(num_reads)]
            start_read = time.perf_counter()
            for k in read_keys:
                _ = db.get(k)
            read_time = time.perf_counter() - start_read
            read_ops_sec = num_reads / read_time if read_time > 0 else 0.0

            # 3. Full-Text Search Latency Benchmark
            search_latencies_ms = []
            search_terms = random.sample(sample_words, k=min(len(sample_words), 10))
            for term in search_terms * 10:
                t0 = time.perf_counter()
                _ = db.search(term)
                t1 = time.perf_counter()
                search_latencies_ms.append((t1 - t0) * 1000.0)

            search_latencies_ms.sort()
            p50_idx = int(len(search_latencies_ms) * 0.50)
            p95_idx = int(len(search_latencies_ms) * 0.95)
            p50_ms = search_latencies_ms[p50_idx] if search_latencies_ms else 0.0
            p95_ms = search_latencies_ms[p95_idx] if search_latencies_ms else 0.0

            db.close()

            # 4. Database Startup & Crash Recovery Latency Benchmark
            t_rec_start = time.perf_counter()
            rec_db = CacheForgeDB(db_path, auto_recover=True)
            t_rec_end = time.perf_counter()
            recovery_ms = (t_rec_end - t_rec_start) * 1000.0

            # 5. Delete Throughput Benchmark
            delete_keys = keys[: min(1000, num_records)]
            start_del = time.perf_counter()
            for k in delete_keys:
                rec_db.delete(k)
            del_time = time.perf_counter() - start_del
            del_ops_sec = len(delete_keys) / del_time if del_time > 0 else 0.0

            db_size = os.path.getsize(rec_db.data_log_path) if os.path.exists(rec_db.data_log_path) else 0
            rec_db.close()

            return BenchmarkResult(
                dataset_records=num_records,
                write_ops_per_sec=write_ops_sec,
                read_ops_per_sec=read_ops_sec,
                delete_ops_per_sec=del_ops_sec,
                search_latency_p50_ms=p50_ms,
                search_latency_p95_ms=p95_ms,
                recovery_time_ms=recovery_ms,
                db_size_bytes=db_size
            )
