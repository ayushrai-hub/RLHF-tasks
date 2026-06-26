# Vault shard hot-reload policy

## reload_applied gate

A workload `active_version` in the export audit reflects `secret_version` only from shards where `reload_applied` is true for that workload. When the highest `shard_seq` row for a workload has `reload_applied` false, `active_version` is empty and `reload_pending` is `"true"`.

## Apply order

Within one bundle ingest, collapse duplicate `(shard_seq, workload_id)` rows using material precedence before persistence. Across stored rows, export and replay order shards by ascending `shard_seq`, then `shard_id`.

## Leak detection

When `log_redacted` is false and `preview` is non-empty, export must emit a `leak_rows` entry with `detail` exactly `unredacted_preview` (never the raw preview text).
