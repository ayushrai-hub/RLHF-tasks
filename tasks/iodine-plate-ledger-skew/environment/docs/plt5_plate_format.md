# PLT5 plate row format

Each segment file is a PLT5 row:

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | magic `PLT5` |
| 4 | 2 | version halfword, little-endian |
| 6 | 2 | plate lane halfword, little-endian |
| 8 | 4 | epoch `u32`, little-endian |
| 12 | 4 | sequence `u32`, little-endian |
| 16 | 4 | payload length `u32`, little-endian |
| 20 | `length` | payload bytes |
| `20 + length` | 4 | stored digest `u32`, little-endian |

## Digest anchors

Each scenario profile may select a digest anchor:

| `digest_anchor` | Digest span (inclusive start, exclusive end) |
|-----------------|---------------------------------------------|
| `0` (epoch) | byte offset `8` through `20 + length` |
| `1` (lane) | byte offset `6` through `20 + length` |

Digest verification recomputes CRC32 over the selected span. The stored digest and all multi-byte numeric fields use little-endian order. Set `digest_match` true when the stored digest equals that CRC32 (the same 32-bit algorithm Python's `binascii.crc32` applies to the digest span).
