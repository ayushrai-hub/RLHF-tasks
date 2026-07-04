# ABWF framed wire format

Magic prefix: `ABWF\x01` (five bytes). All multi-byte integers are big-endian.

## Frame type 0x02 (policy eval)

| Field | Size | Notes |
|-------|------|-------|
| frame_type | 1 | `0x02` |
| tenant_id | 3 | ASCII tenant code |
| eval_seq | 4 | u32 evaluation sequence |
| policy_id_len | 2 | u16 |
| policy_id | policy_id_len | UTF-8 |
| decision | 1 | `0` deny, `1` permit |
| attr_count | 1 | number of attribute pairs |
| attrs | variable | each: key_len u16, key, val_len u16, val |
| utc_offset_sec | 4 | u32 seconds offset from profile epoch |

## Footer frame 0xFF

| Field | Size |
|-------|------|
| frame_type | 1 | `0xFF` |
| batch_id_len | 2 | u16 |
| batch_id | batch_id_len | UTF-8 |
| crc16 | 2 | CRC-16/CCITT-FALSE |

## CRC16-CCITT scope

CRC is computed over bytes starting **immediately after the magic prefix** through the end of `batch_id` in the footer (inclusive of `0xFF`, batch length, and batch bytes). **Do not include the magic bytes or the two CRC bytes** in the checksum input.
