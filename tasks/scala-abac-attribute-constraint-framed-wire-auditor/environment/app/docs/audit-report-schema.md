# Audit report schema (`/app/output/abac-constraint-audit.json`)

Top-level JSON field order when written:

1. `tenant_id` (string)
2. `batch_id` (string)
3. `reported_at_unix` (integer)
4. `decisions` (array)
5. `stats` (object)
6. `audit_hash` (string, 64 hex chars)

Each `decisions[]` object fields: `policy_id`, `effective_decision`, `last_eval_seq`.

`stats` fields: `evals_applied`, `denies_overridden`, `missing_attr_rejected`, `duplicate_skipped`.

`reported_at_unix` = `abac_epoch_base` from profile plus **max** `utc_offset_sec` among ingested eval events for the tenant (0 when none).

## audit_hash

SHA-256 hex digest of UTF-8 payload:

`tenant_id|batch_id|<decisions segment>|<stats segment>`

Decisions segment: policies sorted by `policy_id`, each `policy_id|effective_decision|last_eval_seq` joined with `;`.

Stats segment: `evals_applied=N;denies_overridden=N;missing_attr_rejected=N;duplicate_skipped=N` using export stats values.

## Empty-database export

When the SQLite file has no ingested batches for the exported tenant (`batch_id` is the empty string):

- `decisions` must be `[]` (empty array).
- Every `stats` counter must be `0` (`evals_applied`, `denies_overridden`, `missing_attr_rejected`, `duplicate_skipped`).
- `duplicate_skipped` for empty-batch exports uses the tenant-scoped counter in `abac_tenant_stats` only (not a global sum across other tenants).
- `reported_at_unix` = profile `abac_epoch_base` plus max `utc_offset_sec` for that tenant (0 when the tenant has no eval rows).
- `audit_hash` is still required: compute the canonical payload with an empty decisions segment and the zero stats segment above.
