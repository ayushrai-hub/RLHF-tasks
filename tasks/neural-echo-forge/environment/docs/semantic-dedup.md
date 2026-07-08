# Semantic deduplication

Normalize an object string by lowercasing, trimming ends, and collapsing internal whitespace to a single space.

Two memories are semantic duplicates when they share subject and predicate and any of the following hold:

1. Normalized objects are identical.
2. Normalized objects share a common prefix of at least six characters and the shorter normalized object is a prefix of the longer.
3. Normalized Levenshtein distance is at most 2.

When duplicates are found, keep the memory with higher anchor_ms. On anchor_ms tie, keep higher confidence. On confidence tie, keep lexicographically greater memory_id. Merge losers into merged_from on the winner in ascending memory_id order without duplicates.

Semantic dedup runs once globally after per-group conflict resolution. Tie-breaking during semantic dedup uses conflict_mode from the policy loaded during ingest, not export_mode. closed conflict_mode prefers higher anchor_ms before confidence; open conflict_mode prefers higher confidence before anchor_ms, matching conflict-resolution.md.
