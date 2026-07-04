# Collection snapshot

Path: /app/state/collection-snapshot.json

Fields:
- schema_version: 1
- validated: true when ingest succeeded
- artifacts: parsed roster array sorted by artifact_id
- collection: collection.json object copied verbatim
- collection_snapshot_hash: SHA-256 hex of compact JSON binding artifacts and collection keys except schema_version
