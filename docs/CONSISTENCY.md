# CacheForge — Consistency & Durability Model

This document specifies the exact consistency, durability, and crash guarantees provided by CacheForge.

---

## 1. Durability Guarantees (`fsync`)

* Mutating operations (`set`, `delete`) write a record to `journal.log` first.
* CacheForge issues `os.fsync(fd)` after writing transaction markers to guarantee physical flush from OS page cache to non-volatile storage hardware.
* After writing to `data.log`, `os.fsync(fd)` is issued again before updating in-memory index structures.

---

## 2. Surviving Failure Modes

| Scenario | Behavior / Recovery |
| :--- | :--- |
| **Normal Process Restart** | In-memory key indexes, field indexes, and search inverted indexes are rebuilt from `data.log`. |
| **Process Crash / SIGKILL during write** | Uncommitted WAL entries are discarded upon startup; completed committed WAL entries are replayed; corrupted data log tails are truncated. |
| **Power Failure / Hardware Interrupt** | SHA-256 checksum audit detects incomplete or corrupted binary records and truncates to the last valid checksum offset. |
| **Concurrent Process Access** | `fcntl.flock` file locking serializes writers and protects multi-threaded access via `threading.RLock`. |

---

## 3. Explicit Non-Guarantees

* **Multi-Node Replication**: CacheForge is a single-node embedded storage engine. It does not implement distributed consensus (e.g. Raft/Paxos).
* **Disk Hardware Corruption**: If hardware disk sectors suffer silent multi-bit corruption, CacheForge will detect the corruption via SHA-256 checksum and fail safely, but cannot magically repair damaged disk hardware sectors without backups/snapshots.
