# Reconcile contract

The reconcile subcommand reads /app/state/memory-snapshot.json and /app/state/ingest-staging.json after ingest and writes /app/state/reconcile-report.json before export may run.

## reconcile-report.json fields

| Field | Type | Meaning |
|-------|------|---------|
| reconcile_version | integer | Schema version, currently 1 |
| snapshot_seq | integer | Copied from snapshot.snapshot_seq |
| staging_seq | integer | Copied from ingest-staging.json staging_seq |
| ingest_fingerprint | string | Copied from snapshot.ingest_fingerprint |
| fingerprint_valid | boolean | True when recomputed fingerprint from snapshot body equals ingest_fingerprint |
| staging_digest_sha256 | string | Lowercase hex SHA-256 of ingest-staging.json bytes on disk |
| candidate_digest_sha256 | string | Copied from ingest-staging.json candidate_digest_sha256 |
| conflict_mode | string | Copied from ingest-staging.json conflict_mode |
| export_mode | string | Copied from ingest-staging.json export_mode |

Reconcile fails with exit 2 when either state file is missing, when staging_seq does not equal snapshot_seq, when fingerprint_valid would be false, or when candidate_digest_sha256 does not match the staging ledger.

Export fails with exit 2 when reconcile-report.json is missing or when reconcile-report snapshot_seq, staging_digest_sha256, ingest_fingerprint, or candidate_digest_sha256 do not match the on-disk snapshot and staging ledger.

Default run with no arguments executes ingest, then reconcile, then export in that order. The export subcommand alone does not run reconcile and still requires a current reconcile-report.json written after the snapshot was produced.
