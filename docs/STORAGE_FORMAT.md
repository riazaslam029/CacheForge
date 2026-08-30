# CacheForge — Binary Storage Format Specification

CacheForge uses an explicit, deterministic binary record format powered by Python's standard `struct` module. Persistence is append-only with network byte ordering (`>` big-endian).

---

## 1. Record Binary Layout

Every record in `data.log` and `journal.log` consists of a **70-byte fixed header** followed by **variable-length payloads**:

```
+-----------------------------------------------------------------------------------+
| Field             | Format  | Size     | Description                              |
+-------------------+---------+----------+------------------------------------------+
| MAGIC             | 4s      | 4 bytes  | Magic byte header (b"CFRG")              |
| VERSION           | B       | 1 byte   | Format version integer (1)               |
| RECORD_TYPE       | B       | 1 byte   | Record type (1=SET, 2=DEL, 3=START...)   |
| SEQUENCE          | Q       | 8 bytes  | Monotonic sequence number (uint64)       |
| TIMESTAMP_US      | Q       | 8 bytes  | Creation timestamp in microseconds       |
| EXPIRE_US         | Q       | 8 bytes  | Expiration timestamp (0 = infinite)      |
| KEY_LEN           | I       | 4 bytes  | Length of UTF-8 key data in bytes        |
| VAL_LEN           | I       | 4 bytes  | Length of value data in bytes            |
| FIELDS_LEN        | I       | 4 bytes  | Length of JSON field data in bytes       |
| CHECKSUM          | 32s     | 32 bytes | SHA-256 binary hash over record payload  |
| KEY_DATA          | bytes   | KEY_LEN  | Raw UTF-8 encoded key bytes              |
| VAL_DATA          | bytes   | VAL_LEN  | Raw value bytes (text or binary)         |
| FIELDS_DATA       | bytes   | FIELD_L  | UTF-8 JSON encoded metadata dictionary   |
+-----------------------------------------------------------------------------------+
```

Total Header Size: $4 + 1 + 1 + 8 + 8 + 8 + 4 + 4 + 4 + 32 = 70$ bytes.

---

## 2. Record Types (`RecordType`)

* `1 (SET)`: Key-value set or update operation.
* `2 (DELETE)`: Tombstone deletion record.
* `3 (TX_START)`: Transaction start marker in Write-Ahead Log.
* `4 (TX_COMMIT)`: Transaction commit marker in Write-Ahead Log.
* `5 (TX_ABORT)`: Transaction explicit abort marker.

---

## 3. SHA-256 Checksum Calculation

To prevent bit rot and detect partial or corrupt writes:

1. Extract the 38-byte prefix (Header fields excluding the 32-byte checksum field).
2. Append `KEY_DATA + VAL_DATA + FIELDS_DATA`.
3. Compute `hashlib.sha256()` over the combined byte buffer.
4. Compare computed hash against the stored 32-byte `CHECKSUM`. If mismatched, raise `CorruptionError`.
