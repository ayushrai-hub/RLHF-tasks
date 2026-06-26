# Material precedence and hot reload

Replay reads stored shard rows for one `tenant_id` ordered by **`shard_seq ASC`**, then `shard_id ASC` as tie-break.

## Material precedence per shard_seq

For each `(shard_seq, workload_id)` group, the effective material is the row with the highest source precedence:

1. `env` (highest)
2. `vault_file`
3. `sidecar_mount` (lowest)

Wire encoding maps `env`→2, `vault_file`→1, `sidecar_mount`→0.

When multiple rows share the same `(shard_seq, workload_id)`, only the winning source appears in `shards[]` with `effective_source` and `secret_version` from that row.

## Active version and reload pending

Process shards in `shard_seq` order:

- `active_version` for a workload updates **only** when `reload_applied` is true on the winning row for that `shard_seq` (set to that row's `secret_version`).
- `reload_pending` is `"true"` when the **latest** shard row for the workload (highest `shard_seq`) has `reload_applied` false; otherwise `"false"`.

Rotation is **not** applied to the running process until `reload_applied` is true on the material row that wins at that sequence.

## Leak rows

Emit one `leak_rows[]` entry per stored row where `log_redacted` is false **and** `preview` is non-empty. Use `detail` = `unredacted_preview`. Do **not** copy the preview secret into the export JSON.

## Export stats

- `stats.shard_count` — stored row count for the tenant.
- `stats.duplicate_shards_skipped` — sum of `ingest_files.duplicate_skipped` for that tenant only.
- `stats.workload_count` — distinct workloads in `workloads[]`.
- `stats.reported_at_unix` — `vault_epoch_base` from `/app/config/vault-profile.json` plus the maximum `shard_seq` among stored shards for the tenant (0 when empty).
