# GRSH shard format (version 1)

Binary little-endian records. File extension: `.grsh`.

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | Magic ASCII `GRSH` |
| 4 | 1 | Version `1` |
| 5 | 4 | `shard_id` uint32 |
| 9 | 4 | `drift_ms` int32 (signed milliseconds subtracted from each raw tick) |
| 13 | 4 | `event_count` uint32 |
| 17 | variable | Events (see below) |
| end-4 | 4 | `footer_crc` uint32 IEEE CRC32 |

Each event:

| Size | Field |
|------|-------|
| 4 | `seq` uint32 |
| 4 | `raw_tick` uint32 |
| 2 | `type` uint16 |
| 2 | `payload_len` uint16 |
| N | `payload` bytes (`payload_len` octets) |

**Footer CRC scope:** bytes starting at offset 4 (version byte) through the last event byte (inclusive). The magic and footer CRC itself are excluded.

Reject shards whose magic is not `GRSH`, version is not `1`, or footer CRC mismatches.
