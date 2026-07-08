# Ingest staging ledger

Ingest writes /app/state/ingest-staging.json before /app/state/memory-snapshot.json on every successful ingest. Export reads the staging ledger for export_mode and conflict_mode and must not rewrite it.

## Schema

| Field | Type | Notes |
|-------|------|-------|
| staging_version | integer | Always 1 |
| staging_seq | integer | Matches snapshot_seq written in the same ingest |
| conflict_mode | string | closed or open copied from the policy file used during ingest |
| export_mode | string | closed or open copied from the policy file used during ingest |
| candidate_count | integer | Count of candidate rows appended during ingest before conflict resolution |
| candidate_digest_sha256 | string | Lowercase hex SHA-256 of newline-joined memory_id:discovery_seq lines in candidate append order |

When conflict_mode is absent in the policy file, copy export_mode into conflict_mode.

## candidate_digest_sha256

Hash the UTF-8 payload formed by joining one line per appended candidate with newline characters. Each line is memory_id, colon, decimal discovery_seq with no spaces. Include profile baselines, tool rows, session memory rows, and session correction rows that were appended. Do not include skipped rows, blank lines, or text-only session turns.

## Policy path

Ingest loads the policy file from NEF_POLICY_PATH when set to an absolute path, otherwise /app/data/policies/memory-policy.json. When NEF_POLICY_PATH is set to a non-empty relative path, ingest exits 2. Export must use export_mode and conflict_mode from the staging ledger written during ingest, not re-read the policy file.

## Export coupling

Export fails with exit 2 when ingest-staging.json is missing or when staging_seq does not equal snapshot.snapshot_seq. Export copies staging_digest_sha256 into memory-audit.json as the lowercase hex SHA-256 of the on-disk ingest-staging.json bytes.

Reconcile per /app/docs/reconcile-contract.md must run after ingest and before export. Export fails when reconcile-report.json is missing or stale relative to the snapshot and staging ledger.
