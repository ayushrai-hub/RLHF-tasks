# SQLite schema

Database path default: `/app/data/vault.db`.

## vault_shards

| Column | Type | Notes |
|--------|------|-------|
| shard_id | TEXT PRIMARY KEY | |
| tenant_id | TEXT NOT NULL | |
| shard_seq | INTEGER NOT NULL | |
| workload_id | TEXT NOT NULL | |
| material_source | TEXT NOT NULL | env, vault_file, sidecar_mount |
| reload_applied | INTEGER NOT NULL | 0/1 |
| log_redacted | INTEGER NOT NULL | 0/1 |
| secret_version | TEXT NOT NULL | |
| preview | TEXT | nullable |

Unique index on `(tenant_id, shard_seq, workload_id)`.

## ingest_files

| Column | Type | Notes |
|--------|------|-------|
| bundle_sha256 | TEXT PRIMARY KEY | SHA-256 hex of file bytes |
| tenant_id | TEXT NOT NULL | |
| ingested_at | INTEGER NOT NULL | unix seconds |
| duplicate_skipped | INTEGER NOT NULL | per-file duplicate shard_id count |

Migrations live under `/app/migrations/`.
