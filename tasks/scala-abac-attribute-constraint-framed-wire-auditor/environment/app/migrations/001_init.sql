CREATE TABLE IF NOT EXISTS abac_batches (
  batch_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  file_digest TEXT NOT NULL,
  ingested_at INTEGER NOT NULL,
  evals_applied INTEGER NOT NULL DEFAULT 0,
  denies_overridden INTEGER NOT NULL DEFAULT 0,
  missing_attr_rejected INTEGER NOT NULL DEFAULT 0,
  duplicate_skipped INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS abac_eval_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  eval_seq INTEGER NOT NULL,
  policy_id TEXT NOT NULL,
  decision INTEGER NOT NULL,
  utc_offset_sec INTEGER NOT NULL,
  UNIQUE(batch_id, eval_seq)
);

CREATE TABLE IF NOT EXISTS abac_eval_attrs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id TEXT NOT NULL,
  eval_seq INTEGER NOT NULL,
  attr_key TEXT NOT NULL,
  attr_value TEXT NOT NULL,
  UNIQUE(batch_id, eval_seq, attr_key)
);

CREATE TABLE IF NOT EXISTS abac_policy_state (
  tenant_id TEXT NOT NULL,
  policy_id TEXT NOT NULL,
  effective_decision INTEGER NOT NULL,
  last_eval_seq INTEGER NOT NULL,
  PRIMARY KEY (tenant_id, policy_id)
);

CREATE TABLE IF NOT EXISTS abac_tenant_stats (
  tenant_id TEXT PRIMARY KEY,
  duplicate_skipped INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_abac_eval_tenant ON abac_eval_events(tenant_id, eval_seq);
