# Preservation atlas schema

Path: /app/output/preservation-atlas.json

Fields:
- schema_version: 1
- collection_label (string) — from collection.json
- priority_queue (array) — ordered artifact_id list from preservation staging
- migration_pairs (array) — round-one transcode pairs from preservation staging
- preservation_waves (array) — wave band groupings from preservation staging
- schedule_hash (string) — witness digest from preservation-staging.json
- index_digest (string) — witness digest from index-ledger.json
