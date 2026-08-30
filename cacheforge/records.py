"""
Binary Record Serialization and Checksum Engine.
Uses struct binary packing and SHA-256 checksums to encode persistent records.
"""

from dataclasses import dataclass, field
from enum import IntEnum
import hashlib
import json
import struct
import time
from typing import Dict, Any, Optional, Tuple, BinaryIO

from cacheforge.errors import InvalidRecordError, CorruptionError

MAGIC = b"CFRG"
VERSION = 1

# Struct format: 4s (magic), B (version), B (type), Q (seq), Q (ts), Q (exp_ts), I (k_len), I (v_len), I (f_len), 32s (checksum)
HEADER_FORMAT = ">4sBBQQQIII32s"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # 70 bytes


class RecordType(IntEnum):
    SET = 1
    DELETE = 2
    TX_START = 3
    TX_COMMIT = 4
    TX_ABORT = 5


@dataclass
class Record:
    key: str
    value: bytes
    record_type: RecordType = RecordType.SET
    sequence: int = 0
    timestamp_us: int = 0
    expire_us: int = 0  # 0 means no expiration
    fields: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp_us:
            self.timestamp_us = int(time.time() * 1_000_000)
        if isinstance(self.value, str):
            self.value = self.value.encode("utf-8")

    @property
    def value_str(self) -> str:
        """Helper to get string value decoding utf-8, ignoring non-decodable bytes if binary."""
        try:
            return self.value.decode("utf-8")
        except UnicodeDecodeError:
            return self.value.hex()

    def compute_checksum(self) -> bytes:
        """
        Compute SHA-256 checksum over header metadata and payload data.
        """
        key_bytes = self.key.encode("utf-8")
        fields_bytes = json.dumps(self.fields, sort_keys=True).encode("utf-8") if self.fields else b""
        
        # Build 38-byte payload prefix (header without checksum)
        prefix = struct.pack(
            ">4sBBQQQIII",
            MAGIC,
            VERSION,
            int(self.record_type),
            self.sequence,
            self.timestamp_us,
            self.expire_us,
            len(key_bytes),
            len(self.value),
            len(fields_bytes)
        )
        
        hasher = hashlib.sha256()
        hasher.update(prefix)
        hasher.update(key_bytes)
        hasher.update(self.value)
        hasher.update(fields_bytes)
        return hasher.digest()

    def encode(self) -> bytes:
        """Serialize Record into raw binary payload."""
        key_bytes = self.key.encode("utf-8")
        fields_bytes = json.dumps(self.fields, sort_keys=True).encode("utf-8") if self.fields else b""
        checksum = self.compute_checksum()

        header = struct.pack(
            HEADER_FORMAT,
            MAGIC,
            VERSION,
            int(self.record_type),
            self.sequence,
            self.timestamp_us,
            self.expire_us,
            len(key_bytes),
            len(self.value),
            len(fields_bytes),
            checksum
        )
        return header + key_bytes + self.value + fields_bytes

    @classmethod
    def read_from_stream(cls, stream: BinaryIO) -> Tuple[Optional["Record"], int]:
        """
        Read a single record from a binary file stream.
        Returns tuple of (Record or None if EOF, bytes_read).
        Raises InvalidRecordError or CorruptionError on corrupt data.
        """
        header_bytes = stream.read(HEADER_SIZE)
        if not header_bytes:
            return None, 0
        
        if len(header_bytes) < HEADER_SIZE:
            raise InvalidRecordError(f"Truncated header: read {len(header_bytes)} of {HEADER_SIZE} bytes")

        magic, ver, rec_type_int, seq, ts_us, exp_us, k_len, v_len, f_len, stored_checksum = struct.unpack(
            HEADER_FORMAT, header_bytes
        )

        if magic != MAGIC:
            raise InvalidRecordError(f"Invalid record magic header: {magic!r} (expected {MAGIC!r})")
        if ver != VERSION:
            raise InvalidRecordError(f"Unsupported record format version: {ver}")

        try:
            rec_type = RecordType(rec_type_int)
        except ValueError:
            raise InvalidRecordError(f"Unknown record type integer: {rec_type_int}")

        # Sanity check lengths to avoid allocation attacks
        MAX_KEY_LEN = 64 * 1024  # 64 KB
        MAX_VAL_LEN = 100 * 1024 * 1024  # 100 MB
        MAX_FIELD_LEN = 1 * 1024 * 1024  # 1 MB

        if k_len > MAX_KEY_LEN:
            raise InvalidRecordError(f"Key length {k_len} exceeds max key length limit ({MAX_KEY_LEN})")
        if v_len > MAX_VAL_LEN:
            raise InvalidRecordError(f"Value length {v_len} exceeds max value length limit ({MAX_VAL_LEN})")
        if f_len > MAX_FIELD_LEN:
            raise InvalidRecordError(f"Fields length {f_len} exceeds max fields length limit ({MAX_FIELD_LEN})")

        payload_len = k_len + v_len + f_len
        payload_bytes = stream.read(payload_len)
        if len(payload_bytes) < payload_len:
            raise InvalidRecordError(f"Truncated payload: read {len(payload_bytes)} of {payload_len} bytes")

        key_bytes = payload_bytes[:k_len]
        val_bytes = payload_bytes[k_len:k_len + v_len]
        fields_bytes = payload_bytes[k_len + v_len:]

        key_str = key_bytes.decode("utf-8", errors="replace")

        fields_dict = {}
        if fields_bytes:
            try:
                fields_dict = json.loads(fields_bytes.decode("utf-8"))
            except Exception as e:
                raise CorruptionError(f"Corrupt secondary fields JSON payload: {e}")

        record = cls(
            key=key_str,
            value=val_bytes,
            record_type=rec_type,
            sequence=seq,
            timestamp_us=ts_us,
            expire_us=exp_us,
            fields=fields_dict
        )

        expected_checksum = record.compute_checksum()
        if stored_checksum != expected_checksum:
            raise CorruptionError(
                f"Checksum verification failed for record key '{key_str}' (seq={seq}). "
                f"Stored: {stored_checksum.hex()}, Computed: {expected_checksum.hex()}"
            )

        total_bytes = HEADER_SIZE + payload_len
        return record, total_bytes
