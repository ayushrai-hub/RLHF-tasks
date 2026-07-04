# Offline search shard runner

This repository simulates a web-search ranking service without network access. A plan points at a snapshot manifest, a JSONL query file, a segment cache, and a result limit. The command in `scripts/run_search.sh` loads the current snapshot, searches each shard, merges canonical equivalents, writes a JSON report, and refreshes the cache.

The files in `state/` are intentionally durable runtime state. They may be stale relative to the snapshot. The program must decide when a cached segment is compatible; callers should not need to delete the cache before a correct run.

The product contract lives in `docs/search-contract.md` and `docs/report-schema.md`.
