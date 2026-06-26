# Chunk export contract

`streamd` stages chunked payload replay for QA. Binary schedules live under `/app/data/traces/` and may be nested.

Sizing keys in `/app/config/stream.json` are authoritative.

## Digest limb

FNV-1a 64 runs over each chunk's bytes. Export renders eight lowercase hex digits from the low 32 bits of the hash state. Tail chunks and full chunks share that limb.

## Offsets

Each digest line carries the zero-based byte index where that chunk begins in the schedule payload. Full chunks advance the index by `chunk_size`. Probe and replay CLIs must emit the same offset sequence for every schedule.
