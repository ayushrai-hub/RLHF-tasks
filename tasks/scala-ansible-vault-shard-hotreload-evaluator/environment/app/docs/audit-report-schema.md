# Audit report schema

Export writes pretty-printed JSON (2-space indent) to `/app/output/vault-hotreload-audit.json` (or `--out`). The file ends with a single trailing newline.

## Top-level field order

1. `tenant_id` (string)
2. `shards` (array)
3. `workloads` (array)
4. `leak_rows` (array)
5. `stats` (object)
6. `audit_hash` (64-char lowercase hex SHA-256)

## shards[] object field order

1. `shard_seq` (integer)
2. `workload_id` (string)
3. `effective_source` (string: `env`, `vault_file`, or `sidecar_mount`)
4. `secret_version` (string)

Sort `shards[]` by ascending `(shard_seq, workload_id)`.

## workloads[] object field order

1. `workload_id` (string)
2. `active_version` (string; empty when never reloaded with `reload_applied`)
3. `reload_pending` (string `"true"` or `"false"`)

Sort `workloads[]` by ascending `workload_id`.

## leak_rows[] object field order

1. `workload_id` (string)
2. `shard_seq` (integer)
3. `detail` (string; always `unredacted_preview`)

Sort by ascending `(shard_seq, workload_id)`.

## stats object field order

1. `shard_count` (integer)
2. `duplicate_shards_skipped` (integer)
3. `workload_count` (integer)
4. `reported_at_unix` (integer)

## audit_hash

SHA-256 over UTF-8 bytes of the **compact** JSON (no spaces) of the report object **without** `audit_hash`, with fields in top-level order and nested objects using the field orders above, **plus a single trailing newline character** (`\n`) appended to that compact string before hashing.
