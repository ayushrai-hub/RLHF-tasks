# MSEQ upload log format

Binary logs use magic bytes `0x4D 0x51` (`MQ`). Version must be `1`. Records begin at the magic offset; arbitrary noise bytes before the first record or between records are skipped by scanning forward one byte at a time until `MQ` aligns.

Ingest validation rules (identity checks, transactions, idempotency) are in `/app/docs/mission-ingest-rules.md`. Export flag semantics are in `/app/docs/mission-rollup-rules.md`.

## Waypoint record (`type = 0x01`)

Wire layout after magic:

| Field | Size | Notes |
|-------|------|-------|
| version | 1 | must be `1` |
| type | 1 | `0x01` |
| upload_id_len | 1 | UTF-8 byte length |
| upload_id | variable | |
| seq | 2 | big-endian `u16` |
| lat_e7 | 4 | big-endian `i32` |
| lon_e7 | 4 | big-endian `i32` |
| alt_mm | 4 | big-endian `i32` |
| frame | 1 | MAVLink frame id |
| flags | 1 | see flag bits below |
| crc16 | 2 | big-endian X.25 CRC |

### Waypoint CRC input

CRC is computed over bytes starting at `version` through `flags` inclusive. **Do not** include the `MQ` magic in the CRC input.

When `flags & 0x01` is set, append CRC extra byte `0x4D` to the CRC accumulator input only (not written on the wire).

### Flag bits (persisted on ingest)

| Bit | Mask | Notes |
|-----|------|-------|
| 0 | `0x01` | MAVLink v2 CRC extra on ingest (see above) |
| 1 | `0x02` | Hold — see `/app/docs/mission-rollup-rules.md` |
| 2 | `0x04` | Suppress — see `/app/docs/mission-rollup-rules.md` |

## Footer record (`type = 0xFE`)

Ends every log. Layout after magic:

| Field | Size |
|-------|------|
| version | 1 |
| type | 1 |
| upload_id_len | 1 |
| upload_id | variable |
| expected_count | 2 | big-endian `u16` |
| crc16 | 2 |

Footer CRC input is exactly: `version`, `type`, `upload_id_len`, `upload_id` bytes, `expected_count` (big-endian). No CRC extra byte on footers.
