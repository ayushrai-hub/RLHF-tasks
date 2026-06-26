CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS vault_shards (
  shard_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  shard_seq INTEGER NOT NULL,
  workload_id TEXT NOT NULL,
  material_source TEXT NOT NULL,
  reload_applied INTEGER NOT NULL,
  log_redacted INTEGER NOT NULL,
  secret_version TEXT NOT NULL,
  preview TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_vault_shards_tenant_seq_wl
  ON vault_shards(tenant_id, shard_seq, workload_id);

CREATE TABLE IF NOT EXISTS ingest_files (
  bundle_sha256 TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  ingested_at INTEGER NOT NULL,
  duplicate_skipped INTEGER NOT NULL
);
