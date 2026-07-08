# Retention policy

Policy file fields:

| Field | Type | Meaning |
|-------|------|---------|
| conflict_mode | string | closed or open — copied into ingest-staging.json; governs ingest conflict and semantic dedup tie-breaking |
| export_mode | string | closed or open — copied into ingest-staging.json; export quota uses this mode from the ledger |
| max_per_predicate | integer | Maximum active memories per subject and predicate pair at staging time |
| tier_ttl_ms | object | Maps tier name to TTL milliseconds; null means no expiry |
| export_drop_tiers | string array | Tiers placed into retention_vault at staging |

Bundled policy uses max_per_predicate 2, short TTL 604800000 ms, long TTL null, export_drop_tiers containing ephemeral.

## reference_anchor_ms

Set to the maximum anchor_ms across profile baselines (0), tool rows, and session rows including non-memory turns.

## Staging classification

After conflict resolution and semantic dedup:

1. Memories whose tier appears in export_drop_tiers move to retention_vault.
2. Memories whose tier is short and reference_anchor_ms minus anchor_ms exceeds tier_ttl_ms.short move to retention_vault.
3. For each subject and predicate pair, sort remaining memories by anchor_ms descending, then confidence descending, then memory_id descending. Keep the first max_per_predicate entries in active_memories. Move the rest to retention_vault.

active_memories array order is ascending anchor_ms, then ascending memory_id.

retention_vault array order is ascending anchor_ms, then ascending memory_id.

superseded_memories array order is ascending discovery_seq.

## Export modes

closed mode (bundled default): for each subject and predicate pair, keep the active memory with highest anchor_ms. When anchor_ms ties, keep higher confidence. When confidence ties, keep lexicographically greater memory_id.

open mode: for each subject and predicate pair, keep the active memory with highest confidence. When confidence ties, keep higher anchor_ms. When anchor_ms ties, keep lexicographically greater memory_id.

export_mode from policy is copied into ingest-staging.json and governs export-time quota when multiple active rows remain per subject and predicate. conflict_mode from policy is copied into ingest-staging.json and governs ingest conflict tie-breaking for competing candidates with the same subject and predicate, including semantic dedup. Retrieval index ordering per export-artifacts.md follows discovery_seq only.

## Export

Export reads active_memories only. It does not apply additional retention filtering. Export applies export-time quota documented in export-artifacts.md using export_mode from the staging ledger.
