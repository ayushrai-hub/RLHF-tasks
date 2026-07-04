# Ingest manifest

Path: /app/state/ingest-manifest.json

Binds collection_snapshot_hash, redundancy_hash, rollup_hash, index_digest, schedule_hash, run_sequence.
ingest_complete true only when all binds written.
manifest_hash covers manifest fields except itself.
Re-intake on unchanged roster keeps collection_snapshot_hash stable and increments run_sequence.
