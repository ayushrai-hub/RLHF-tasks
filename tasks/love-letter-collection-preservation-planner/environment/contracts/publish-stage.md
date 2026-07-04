# Emit stage

Emit reads /app/state/collection-snapshot.json, redundancy-pools.json, migration-rollup.json, index-ledger.json, preservation-staging.json, ingest-manifest.json.
Verifies manifest binds and within_storage_budget true.
Writes /app/output/preservation-atlas.json and /app/output/preservation-report.json.
