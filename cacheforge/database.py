"""
CacheForge Core Database Engine.
Integrates binary persistent storage, Write-Ahead Logging (WAL), crash recovery,
secondary field indexing, full-text search, TTL expiration, compaction, and file locking.
"""

import json
import os
import shutil
import time
from typing import Dict, List, Tuple, Optional, Any, Union

from cacheforge.records import Record, RecordType
from cacheforge.locking import DatabaseLock
from cacheforge.journal import Journal
from cacheforge.recovery import RecoveryEngine, RecoveryReport
from cacheforge.integrity import IntegrityChecker, IntegrityReport
from cacheforge.ttl import TTLEngine
from cacheforge.index import SecondaryIndex
from cacheforge.search import FullTextSearchEngine
from cacheforge.compaction import Compactor, CompactionReport
from cacheforge.errors import DatabaseError, KeyNotFoundError, TTLError


class CacheForgeDB:
    """
    Main embedded storage engine instance for CacheForge.
    """

    def __init__(self, db_dir: str, auto_recover: bool = True):
        self.db_dir = os.path.abspath(db_dir)
        os.makedirs(self.db_dir, exist_ok=True)
        
        self.data_log_path = os.path.join(self.db_dir, "data.log")
        self.journal_path = os.path.join(self.db_dir, "journal.log")
        self.manifest_path = os.path.join(self.db_dir, "manifest")
        self.lock_path = os.path.join(self.db_dir, "lock")
        self.index_dir = os.path.join(self.db_dir, "index")
        self.snapshots_dir = os.path.join(self.db_dir, "snapshots")

        os.makedirs(self.index_dir, exist_ok=True)
        os.makedirs(self.snapshots_dir, exist_ok=True)

        self._lock = DatabaseLock(self.lock_path)
        self._journal = Journal(self.journal_path)

        # In-memory index structures
        self._key_index: Dict[str, Record] = {}
        self._secondary_index = SecondaryIndex()
        self._search_engine = FullTextSearchEngine()

        self._sequence_number = 0
        self._created_at_us = TTLEngine.now_us()
        self.last_recovery_report: Optional[RecoveryReport] = None

        with self._lock:
            self._load_or_init_manifest()
            if auto_recover:
                self.recover()
            self._journal.open()

    def _next_sequence(self) -> int:
        self._sequence_number += 1
        return self._sequence_number

    def _load_or_init_manifest(self):
        """Read or create manifest JSON metadata."""
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._sequence_number = data.get("sequence_number", 0)
                    self._created_at_us = data.get("created_at_us", TTLEngine.now_us())
            except Exception as e:
                raise DatabaseError(f"Failed to read database manifest: {e}")
        else:
            self._save_manifest()

    def _save_manifest(self):
        """Save updated manifest metadata."""
        data = {
            "engine": "CacheForge",
            "version": 1,
            "sequence_number": self._sequence_number,
            "created_at_us": self._created_at_us,
            "updated_at_us": TTLEngine.now_us()
        }
        tmp_path = self.manifest_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp_path, self.manifest_path)

    def recover(self) -> RecoveryReport:
        """Execute crash recovery scan and rebuild in-memory indexes."""
        report, active_map, valid_list = RecoveryEngine.recover_database(self.db_dir)
        self.last_recovery_report = report
        
        self._key_index.clear()
        self._secondary_index.clear()
        self._search_engine.clear()

        now_us = TTLEngine.now_us()
        for key, record in active_map.items():
            if not TTLEngine.is_expired(record, now_us=now_us):
                self._key_index[key] = record
                if record.fields:
                    self._secondary_index.index_record(key, record.fields)
                self._search_engine.index_record(key, record.value_str)

        if valid_list:
            max_seq = max(r.sequence for r in valid_list)
            if max_seq > self._sequence_number:
                self._sequence_number = max_seq
                self._save_manifest()

        return report

    def set(
        self,
        key: str,
        value: Union[str, bytes],
        ttl: Optional[float] = None,
        fields: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store a key-value record with optional TTL (seconds) and secondary field metadata.
        """
        if not key or not isinstance(key, str):
            raise DatabaseError("Key must be a non-empty string")

        val_bytes = value.encode("utf-8") if isinstance(value, str) else value
        expire_us = TTLEngine.calculate_expire_us(ttl)

        with self._lock:
            seq = self._next_sequence()
            record = Record(
                key=key,
                value=val_bytes,
                record_type=RecordType.SET,
                sequence=seq,
                expire_us=expire_us,
                fields=fields or {}
            )

            # 1. Write operation to WAL
            self._journal.write_record(record, fsync=True)

            # 2. Append to persistent data log
            with open(self.data_log_path, "a+b") as f:
                f.write(record.encode())
                f.flush()
                os.fsync(f.fileno())

            # 3. Update in-memory state
            old_record = self._key_index.get(key)
            if old_record and old_record.fields:
                self._secondary_index.unindex_record(key, old_record.fields)

            self._key_index[key] = record
            if record.fields:
                self._secondary_index.index_record(key, record.fields)
            self._search_engine.index_record(key, record.value_str)
            self._save_manifest()

            return True

    def get(self, key: str) -> Optional[Record]:
        """
        Retrieve record by key. Returns None if missing or expired.
        """
        with self._lock:
            record = self._key_index.get(key)
            if record is None:
                return None
            
            if TTLEngine.is_expired(record):
                # Lazy removal of expired record from active index
                self._purge_key_memory(key)
                return None
            
            return record

    def get_value(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Helper to get string value directly."""
        rec = self.get(key)
        if rec is None:
            return default
        return rec.value_str

    def exists(self, key: str) -> bool:
        """Check if active unexpired key exists."""
        return self.get(key) is not None

    def delete(self, key: str) -> bool:
        """
        Delete a key from database (appends tombstone DELETE record to log).
        """
        with self._lock:
            if not self.exists(key):
                return False

            seq = self._next_sequence()
            tombstone = Record(
                key=key,
                value=b"",
                record_type=RecordType.DELETE,
                sequence=seq
            )

            # Write WAL & data log
            self._journal.write_record(tombstone, fsync=True)
            with open(self.data_log_path, "a+b") as f:
                f.write(tombstone.encode())
                f.flush()
                os.fsync(f.fileno())

            self._purge_key_memory(key)
            self._save_manifest()
            return True

    def _purge_key_memory(self, key: str):
        """Remove key from in-memory index structures."""
        record = self._key_index.pop(key, None)
        if record and record.fields:
            self._secondary_index.unindex_record(key, record.fields)
        self._search_engine.unindex_record(key)

    def ttl(self, key: str) -> float:
        """
        Get remaining TTL in seconds for key.
        Returns -1.0 if key has no expiration.
        Raises KeyNotFoundError if key doesn't exist or is expired.
        """
        rec = self.get(key)
        if rec is None:
            raise KeyNotFoundError(key)
        return TTLEngine.remaining_ttl_seconds(rec)

    def expire(self, key: str, ttl_seconds: float) -> bool:
        """
        Set or update expiration TTL for an existing key.
        """
        with self._lock:
            rec = self.get(key)
            if rec is None:
                raise KeyNotFoundError(key)
            return self.set(key, rec.value, ttl=ttl_seconds, fields=rec.fields)

    def persist(self, key: str) -> bool:
        """
        Remove TTL expiration from an existing key.
        """
        with self._lock:
            rec = self.get(key)
            if rec is None:
                raise KeyNotFoundError(key)
            if rec.expire_us == 0:
                return True
            return self.set(key, rec.value, ttl=None, fields=rec.fields)

    def query(self, fields: Dict[str, Any]) -> List[Record]:
        """
        Query for active records matching secondary field conditions.
        """
        with self._lock:
            matching_keys = self._secondary_index.query(fields)
            results = []
            for k in matching_keys:
                rec = self.get(k)
                if rec is not None:
                    results.append(rec)
            return results

    def search(self, query_text: str) -> List[Tuple[Record, float]]:
        """
        Perform full-text inverted search over record values.
        Returns list of (Record, relevance_score).
        """
        with self._lock:
            active_keys = set(self._key_index.keys())
            ranked = self._search_engine.search(query_text, active_keys=active_keys)
            results = []
            for key, score in ranked:
                rec = self.get(key)
                if rec is not None:
                    results.append((rec, score))
            return results

    def cleanup(self) -> int:
        """
        Eagerly purge all expired records from memory index.
        """
        with self._lock:
            now_us = TTLEngine.now_us()
            expired_keys = [
                k for k, rec in self._key_index.items()
                if TTLEngine.is_expired(rec, now_us=now_us)
            ]
            for k in expired_keys:
                self._purge_key_memory(k)
            return len(expired_keys)

    def compact(self) -> CompactionReport:
        """Perform database log compaction to reclaim space."""
        with self._lock:
            self._journal.close()
            report = Compactor.compact_database(self.db_dir)
            self._journal.open()
            self.recover()
            return report

    def verify(self) -> IntegrityReport:
        """Perform integrity checksum check on persistent log files."""
        with self._lock:
            return IntegrityChecker.verify_database(self.db_dir)

    def snapshot(self, name: Optional[str] = None) -> str:
        """
        Create a point-in-time persistent snapshot copy of the database.
        """
        with self._lock:
            snap_name = name or f"snapshot_{int(time.time())}"
            target_dir = os.path.join(self.snapshots_dir, snap_name)
            if os.path.exists(target_dir):
                shutil.rmtree(target_dir)
            
            os.makedirs(target_dir, exist_ok=True)
            for fname in ["data.log", "journal.log", "manifest"]:
                src = os.path.join(self.db_dir, fname)
                if os.path.exists(src):
                    shutil.copy2(src, os.path.join(target_dir, fname))

            self._secondary_index.save_to_file(os.path.join(target_dir, "fields.idx"))
            self._search_engine.save_to_file(os.path.join(target_dir, "search.idx"))
            return target_dir

    def export_data(self, json_filepath: str):
        """Export active database state as JSON file."""
        with self._lock:
            records_data = []
            for rec in self._key_index.values():
                if not TTLEngine.is_expired(rec):
                    records_data.append({
                        "key": rec.key,
                        "value": rec.value_str,
                        "fields": rec.fields,
                        "expire_us": rec.expire_us
                    })
            with open(json_filepath, "w", encoding="utf-8") as f:
                json.dump(records_data, f, indent=2)

    def import_data(self, json_filepath: str) -> int:
        """Import key-value records from JSON file."""
        with open(json_filepath, "r", encoding="utf-8") as f:
            records_data = json.load(f)
        
        count = 0
        with self._lock:
            for item in records_data:
                key = item.get("key")
                val = item.get("value")
                fields = item.get("fields")
                if key and val is not None:
                    self.set(key, val, fields=fields)
                    count += 1
        return count

    def stats(self) -> Dict[str, Any]:
        """Return comprehensive live database statistics."""
        with self._lock:
            now_us = TTLEngine.now_us()
            total_records = len(self._key_index)
            expired_count = sum(1 for r in self._key_index.values() if TTLEngine.is_expired(r, now_us))
            live_records = total_records - expired_count

            data_size = os.path.getsize(self.data_log_path) if os.path.exists(self.data_log_path) else 0
            journal_size = os.path.getsize(self.journal_path) if os.path.exists(self.journal_path) else 0

            sec_stats = self._secondary_index.get_stats()
            search_stats = self._search_engine.get_stats()
            integrity = self.verify()

            return {
                "database_dir": self.db_dir,
                "sequence_number": self._sequence_number,
                "total_records": total_records,
                "live_records": live_records,
                "expired_records": expired_count,
                "data_size_bytes": data_size,
                "journal_size_bytes": journal_size,
                "indexed_fields_count": sec_stats["indexed_fields"],
                "search_terms_count": search_stats["unique_terms"],
                "integrity_status": "VALID" if integrity.is_valid else "CORRUPT",
                "recovery_status": self.last_recovery_report.status if self.last_recovery_report else "CLEAN"
            }

    def close(self):
        """Close journal log and release file descriptors."""
        with self._lock:
            self._journal.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
