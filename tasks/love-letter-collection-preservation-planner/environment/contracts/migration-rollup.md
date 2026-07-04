# migration-rollup

Path: /app/state/migration-rollup.json

Written during intake after collection-snapshot.json is certified.

Fields:
- schema_version (integer) — always 1
- format_groups (object) — maps source FORMAT tag to sorted artifact_id lists
- format_count (integer) — number of format groups
- collection_snapshot_hash (string) — copied from collection-snapshot.json
- rollup_hash (string) — sha256 of canonical body without rollup_hash

Rollup groups artifacts by FORMAT from letterfolio descriptors, not by keepsake box name.
