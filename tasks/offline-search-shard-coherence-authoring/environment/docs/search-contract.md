# Search contract

The runner is a deterministic offline version of a federated web-search merge. It accepts a plan JSON with these fields: `manifest`, `queries`, `cache`, and `limit`. Paths may be absolute or relative to the plan file's directory. The public command may override the output path.

## Snapshot hash

Every run computes one `snapshot_hash`. The digest algorithm is SHA-256 and the rendered value is `sha256:` plus lowercase hex. Hash input is the concatenation, in this order, of the bytes of the manifest JSON file, the canonical TSV file named by the manifest, the robots TSV file named by the manifest, and every shard file listed by the manifest in manifest order. Before each file's bytes, the relative manifest path for that file and one newline byte are added; after each file's bytes, one newline byte is added. A changed shard, canonical table, robots table, or manifest must therefore change the digest even if query ids are unchanged.

## Query parsing

Query text is ASCII-normalized by lowercasing and splitting unquoted text on non-alphanumeric bytes. Quoted spans such as `"reef lantern"` are phrases; their words also count as ordinary query terms. Duplicate terms are collapsed while preserving first appearance order. Empty queries produce no results.

## Robots, canonical grouping, and selected document

Robots rules are TSV lines of `url_prefix<TAB>allow|disallow`. The longest matching prefix for the raw fetched document URL wins; no matching rule means allow. Robots are evaluated before canonical grouping, and a disallowed raw URL contributes nothing to ranking, supporting URLs, or provenance.

Canonical rules are TSV lines of `raw_url<TAB>canonical_url`. A document with no table entry is canonical to its own raw URL. All allowed documents with the same canonical URL are one result. The selected document for the result is the allowed raw document in that canonical group with the highest document score; ties inside a group use published date descending, then raw URL ascending. `supporting_urls` is the sorted list of allowed raw URLs in the group.

## Score

For a document, count query-term occurrences separately in tokenized `title`, `body`, and `anchor_text`:

`score = 6*title_hits + 1*body_hits + 3*anchor_hits + 12*title_phrase_hits + 5*body_phrase_hits + quality + freshness`

Phrase hits count case-insensitive contiguous appearances of each quoted phrase in the lowercased title or body text. `quality` is the document's numeric quality field. `freshness` uses the manifest `freshness_epoch` date: if `published` is after the epoch, freshness is `0`; otherwise it is `max(0, 90 - age_days) / 30`, where `age_days` is whole days from `published` to `freshness_epoch`. Render result scores rounded to three decimal places.

`matched_terms` is the query's unique term list filtered to terms that appear at least once in the selected document's title, body, or anchor text. Terms stay in query order.

## Result ordering and cache compatibility

Results are sorted by score descending, published date descending, then canonical URL ascending. Ranks start at 1 after applying the plan `limit`.

The segment cache stores per-query, per-shard candidate lists. A cache entry may be reused only when all of these fields match the current run: `snapshot_hash`, `query_id`, `query_text`, `shard`, and `limit`. The runner may keep or drop older incompatible entries, but it must write compatible entries for the current run and segment provenance must mark whether each segment was reused (`hit`), recomputed because no compatible entry existed (`miss`), or recomputed because only incompatible entries existed (`stale`).
