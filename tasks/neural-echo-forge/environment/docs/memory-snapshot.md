# Memory snapshot

Path: /app/state/memory-snapshot.json

## Top-level fields

| Field | Type | Notes |
|-------|------|-------|
| snapshot_version | integer | Always 1 |
| snapshot_seq | integer | Prior snapshot_seq plus 1, or 1 when no prior snapshot |
| lines_skipped | integer | Malformed rows skipped during ingest |
| reference_anchor_ms | integer | Maximum anchor_ms observed across profiles, tools, and session rows |
| sources_loaded | string array | Basenames in ingest discovery order |
| active_memories | array | Memory records retained after conflict, dedup, and retention classification |
| superseded_memories | array | Losers from conflict resolution and semantic dedup |
| retention_vault | array | Memories staged but excluded from export per retention-policy.md |
| ingest_fingerprint | string | Lowercase hex sha256 per fingerprint rules below |

## Memory record entry

| Field | Type | Notes |
|-------|------|-------|
| memory_id | string | Stable identifier |
| subject | string | Memory subject key |
| predicate | string | Memory predicate key |
| object | string | Canonical object string after normalization is not applied to stored object |
| confidence | number | 0.0 through 1.0 |
| tier | string | ephemeral, short, or long |
| anchor_ms | integer | Effective timestamp |
| source | string | profile_baseline, session_memory, session_correction, or tool_invoke |
| discovery_seq | integer | Monotonic ingest order among appended candidates only; see memory-contract.md |

Optional merged_from string array lists memory_ids merged by semantic dedup.

## ingest_fingerprint

Concatenate with newline separators in this exact order:

1. reference_anchor_ms as decimal string
2. sources_loaded joined by comma without spaces
3. For each active_memories entry in array order: memory_id, subject, predicate, object, anchor_ms joined by colon
4. For each retention_vault entry in array order: memory_id, subject, predicate joined by colon

Hash the UTF-8 bytes with SHA-256 and emit lowercase hex.

## Staging versus export

The snapshot retains retention_vault rows that export omits. Export must not remove vault rows from the snapshot file.
