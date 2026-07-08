# Export artifacts

## memory-records.json

Object with fields:

| Field | Type | Notes |
|-------|------|-------|
| snapshot_seq | integer | Copied from snapshot |
| reference_anchor_ms | integer | Copied from snapshot |
| records | array | Subset of active_memories after export quota |

Export quota: for each subject and predicate pair, keep at most one record. Use export_mode from /app/state/ingest-staging.json — closed prefers highest anchor_ms, open prefers highest confidence; tie-breakers are documented in retention-policy.md.

records array order is ascending subject, then ascending predicate, then ascending memory_id.

## retrieval-index.json

Object mapping subject string to predicate map. Each predicate maps to an array of memory_id strings sorted ascending. Include only memory_ids present in memory-records.json records.

Top-level subject keys are sorted ascending. Within each subject object, predicate keys are ordered by ascending earliest discovery_seq among exported records for that predicate; when earliest discovery_seq ties, order predicate names ascending. This ordering is not alphabetical when discovery order differs.

## memory-audit.json

| Field | Type | Notes |
|-------|------|-------|
| snapshot_digest_sha256 | string | Lowercase hex SHA-256 of snapshot file bytes |
| export_generation | integer | Prior export_generation plus 1, or 1 when absent |
| active_staged | integer | Count of active_memories in snapshot |
| vault_staged | integer | Count of retention_vault in snapshot |
| superseded_staged | integer | Count of superseded_memories in snapshot |
| exported_records | integer | Count of records in memory-records.json |
| lines_skipped | integer | Copied from snapshot |
| staging_digest_sha256 | string | Lowercase hex SHA-256 of ingest-staging.json bytes on disk |

Export must read snapshot bytes from disk when computing snapshot_digest_sha256. Export must read ingest-staging.json bytes from disk when computing staging_digest_sha256. Export requires a current reconcile-report.json per /app/docs/reconcile-contract.md.
