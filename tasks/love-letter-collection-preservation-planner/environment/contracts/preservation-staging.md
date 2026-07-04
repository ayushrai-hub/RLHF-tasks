# Preservation staging

Path: /app/state/preservation-staging.json

priority_queue ordered by descending priority_score then artifact_id ascending.
priority_queue is a JSON array of artifact_id strings only, ranked per priority-seeding.md, not objects carrying scores.
priority_score = redundancy - len(crossref) - abs(media_slot)/12.
migration_pairs: JSON array of round-one transcode pair objects (not two-element arrays).
Each object must carry exactly these keys:
- migration_id (string) — r1-m1 through r1-m{n/2} in pair order
- primary (string) — artifact_id at priority_queue seed index i
- replica (string) — artifact_id at priority_queue seed index n-1-i
- round (integer) — always 1 for round-one bracket pairing
Pairing rule: standard bracket seed[i] vs seed[n-1-i] for i in 0..n/2-1.
Reject ingest when FRAGILE conflicts appear in a pairing.
preservation_waves per preservation-wave-bands.md.
within_storage_budget per storage-budget.md.
schedule_hash binds schema_version, priority_queue, migration_pairs, preservation_waves, within_storage_budget.
