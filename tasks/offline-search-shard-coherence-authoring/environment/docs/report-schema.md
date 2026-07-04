# Report schema

The report is JSON with `schema_version` equal to `offline-search-run-v1`.

Top-level fields:

- `schema_version`: string.
- `snapshot_id`: string from the manifest.
- `snapshot_hash`: `sha256:` digest described in `search-contract.md`.
- `limit`: integer copied from the plan.
- `queries`: array of query reports in query-file order.
- `provenance`: object describing source paths and segment decisions.

Query report fields:

- `id`: query id from JSONL.
- `text`: query text from JSONL.
- `results`: array of result objects sorted by the contract.

Result fields:

- `rank`: one-based integer within the query result list.
- `canonical_url`: canonical URL used as the dedupe key.
- `selected_url`: raw URL of the selected allowed document.
- `title`: selected document title.
- `score`: number rounded to three decimal places.
- `published`: selected document publication date in `YYYY-MM-DD` format.
- `source_shard`: shard id from the manifest entry that supplied the selected document.
- `matched_terms`: array of unique query terms from the selected document, in query order.
- `supporting_urls`: sorted array of allowed raw URLs in the canonical group.

Provenance fields:

- `manifest_path`, `query_path`, and `cache_path`: absolute paths used for the run.
- `segments`: one row for every query/shard pair. Each row has `query_id`, `shard`, `snapshot_hash`, `cache_status`, and `candidate_count`. `cache_status` is one of `hit`, `miss`, or `stale`.
