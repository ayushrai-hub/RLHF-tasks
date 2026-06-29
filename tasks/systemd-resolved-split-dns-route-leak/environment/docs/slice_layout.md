# Binary slice layout (.rt)

All multi-byte integers are big-endian unsigned.

## Header (16 bytes)

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | Magic `RTv1` (0x52 0x54 0x76 0x31) |
| 4 | 4 | `epoch` — link registration epoch |
| 8 | 2 | `link_id` — active link identifier |
| 10 | 2 | `band_class` — effective downgrade band (0–3) |
| 12 | 4 | `row_count` — number of row records |

## Row record (32 bytes each, starts at offset 16)

| Offset | Size | Field |
|--------|------|-------|
| 0 | 16 | `name_digest` — first 16 bytes of sha256(qname) |
| 16 | 4 | `qclass_code` — 1=public, 2=internal |
| 20 | 4 | `scope_code` — 1=external link, 2=internal link |
| 24 | 4 | `seq` — emission sequence within epoch |
| 28 | 4 | `flags` — reserved, must be 0 |

## Canonical byte order for digest

Concatenate: header bytes + rows sorted by (`epoch`, `seq`, `name_digest`).

Fixture slices under `fixtures/blk/` use the same layout. `tc.rt` is the primary authority slice; `td.rt` is a variant with bumped epoch for matrix arms that reorder link attachment.
