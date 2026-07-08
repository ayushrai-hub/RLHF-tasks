# Columnar segment input

Segments live under `/app/fixtures/` as `segment_01.json` through `segment_20.json`.
Override the directory with `COLUMNAR_FIXTURE_DIR` for verifier-only fixtures.

Each segment file:

```
{
  "segment_id": "segment_XX",
  "row_count": int,
  "schema_version": int,
  "columns": [ ... ],
  "pages": [ { "page_id": int, "column": string, "checksum_hex": string } ],
  "statistics": { "<column>": { "min", "max", "null_count", "distinct_count" } }
}
```

Optional blocks: `row_group`, `metadata`, `pruning`, `compaction`, `parallel_encode`.

## Column encodings

`plain` — `values` array length must equal `row_count`. Otherwise emit `COLUMN_ROW_MISMATCH`.

`dictionary` — `dictionary` string array and `indices` int array. Indices use base 0.
Decode one token per index. Out-of-range indices (`index < 0` or `index >= len(dictionary)`) decode to the placeholder token `INVALID` and emit `DICT_INDEX_OOB`.

Optional `dictionary_revision` and `dictionary_snapshots` for incremental dictionary writes.
When `dictionary_revision > 0` and snapshots are present, compute the prior allowed dictionary size as the minimum snapshot dictionary length among snapshots with `revision < dictionary_revision`. Any index `>=` that allowed size emits `DICT_INCREMENTAL_STALE` even if the index is in range for the current dictionary.

`rle` — `runs` array of `{ "value", "length" }`. Expanded length must equal `row_count`.
If the expanded run length differs, emit `RLE_LENGTH_MISMATCH` (never `COLUMN_ROW_MISMATCH` for this case alone). Decoded output length is the expanded run length, which may be shorter or longer than `row_count`.

`bitpack` — `bit_width` int and `values` int array. Every value must satisfy `0 <= value < 2**bit_width`
or emit `BITPACK_OVERFLOW`. If `len(values) != row_count`, also emit `COLUMN_ROW_MISMATCH`.

`delta` — `base` int and `deltas` int array. Decoded values are running sums starting at `base`.
Optional `validated_base` must equal `base` when present (`DELTA_BASE_WRONG` otherwise).
If `len(deltas) != row_count`, emit `COLUMN_ROW_MISMATCH`.

`mirror_plain` on a dictionary column holds the expected decoded values for divergence checks.
Compare after dictionary decode (including `INVALID` placeholders). Mismatch emits `DECODE_DIVERGENCE`.

## Page checksum

For each page entry, `checksum_hex` is the first 16 hex chars of SHA256 over
`column + ":" + comma-separated decoded string values` for that column.
Compute against the actual decoded slice for that column, including `INVALID` placeholders.
Encoding faults do not suppress page checksum comparison.

## Decoding

Decode every column independently to a string slice. The decoded length is encoding-specific
(plain/bitpack: `len(values)`; dictionary: `len(indices)`; rle: sum of run lengths; delta: `len(deltas)`).
It need not equal `row_count` when a length fault is present.

Nulls use JSON `null` and decode to the literal token `NULL` in checksum and reconstruction payloads.

Always run statistics, page checksum, pruning, and reconstruction against the decoded slices even when encoding fault codes are also emitted.
