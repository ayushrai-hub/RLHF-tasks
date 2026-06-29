# GRPL pack transport format

`/app/scripts/replay-pack.sh CHRONICLE.json OUTPUT.grpl` writes a binary container:

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | Magic `GRPL` |
| 4 | 1 | Version `1` |
| 5 | 4 | `payload_len` uint32 LE — byte length of gzip body |
| 9 | 4 | `header_crc` uint32 LE IEEE CRC32 of bytes at offsets 4–12 (version + payload_len, 5 bytes) |
| 13 | N | `gzip -cn` of the chronicle JSON (no filename, no timestamp, raw deflate stream) |

`/app/scripts/replay-unpack.sh INPUT.grpl` writes chronicle JSON to stdout:

1. Verify magic `GRPL` and version `1`.
2. Read `payload_len` and `header_crc`; recompute CRC32-IEEE over bytes 4–12 and reject on mismatch.
3. Gunzip exactly `payload_len` bytes and emit UTF-8 JSON.

Both scripts exit non-zero on format errors.
