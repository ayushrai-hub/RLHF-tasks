# Vault shard frame format (`.vshard`)

Bundles are a byte stream of one or more **frames**. Leading noise bytes may appear before the first frame; the ingest parser must **resync** on the two-byte magic `VS` (0x56 0x53).

## Frame layout (big-endian)

| Offset | Size | Field |
|--------|------|-------|
| 0 | 2 | Magic `V` `S` |
| 2 | 1 | `version` (must be `1`) |
| 3 | 1 | `flags` (reserved, must be `0`) |
| 4 | 4 | `shard_seq` (uint32) |
| 8 | 2 | `tenant_id` length |
| 10 | n | `tenant_id` UTF-8 |
| 10+n | 2 | `shard_id` length |
| | m | `shard_id` UTF-8 (unique per frame) |
| | 2 | `workload_id` length |
| | k | `workload_id` UTF-8 |
| | 1 | `material_source` (`0`=sidecar_mount, `1`=vault_file, `2`=env) |
| | 1 | `reload_applied` (`0`=false, `1`=true) |
| | 1 | `log_redacted` (`0`=false, `1`=true) |
| | 2 | `secret_version` length |
| | p | `secret_version` UTF-8 |
| | 2 | `preview` length (may be `0`) |
| | q | `preview` UTF-8 (only when length > 0) |
| end-2 | 2 | `frame_crc16` uint16 |

## CRC-16/CCITT-FALSE

Polynomial `0x1021`, init `0xFFFF`, no reflection, no final xor. The CRC covers bytes **from `version` through the end of `preview`** (offsets 2 through end-3 inclusive). **Do not** include the magic bytes or the CRC field itself.

Declared CRC is 4 lowercase hex digits compared to the computed value.

## Ingest rules

- Compute `bundle_sha256` as SHA-256 hex over the **entire file bytes**.
- If `bundle_sha256` was already ingested, skip the file (idempotent).
- All frames in one bundle must share the same `tenant_id`.
- Apply frames in ascending **`shard_seq`** order (not physical file order).
- Duplicate `shard_id` within a bundle increments `duplicate_skipped` and does not insert a second row.
- Multiple frames in one bundle with the same `(shard_seq, workload_id)` are collapsed to the highest-precedence `material_source` before insert (see `/app/docs/material-precedence.md`).
- Conflicting `(tenant_id, shard_seq, workload_id)` with a different `shard_id` already stored in the database fails the whole file and rolls back.
- Ingest runs in a **single SQLite transaction**; any bad frame rolls back all inserts and must not record `ingest_files`.
