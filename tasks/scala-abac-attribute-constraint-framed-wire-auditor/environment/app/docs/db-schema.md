# SQLite schema (`/app/data/abac.db`)

Tables: `abac_batches`, `abac_eval_events`, `abac_eval_attrs`, `abac_policy_state`, `abac_tenant_stats`.

`abac_tenant_stats.duplicate_skipped` accumulates duplicate `eval_seq` skips **per tenant** across batches.

`abac_eval_events` rows are loaded for replay/export in **`eval_seq` ascending** order.

Ingest runs in a transaction: failed CRC or replay errors roll back without persisting partial batches.
