# Mount slice byte layout (MNT1)

| Offset | Size | Field |
|--------|------|-------|
| 0 | 4 | Magic `MNT1` |
| 4 | 2 | uint16 record count |
| 6 | 6×N | Records: uint16 slot_id, uint32 workdir_hash |

Digest anchor uses bytes `[0:32]` from `tc.mnt` regardless of lane `blk_slice`.
