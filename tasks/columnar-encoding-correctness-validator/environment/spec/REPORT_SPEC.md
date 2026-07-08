# Encoding integrity report

Write exactly one file: `/app/output/encoding_integrity_report.json`.
UTF-8 JSON with two-space indent and a trailing newline. Repeated runs must be byte identical.

## Top level

```
{
  "summary": { ... },
  "segments": [ ... ]
}
```

Keys are exactly `summary` then `segments`.

### JSON key order (normative)

Top level: `summary`, `segments`.

`summary`: `segments_analyzed`, `segments_passing`, `segments_failing`, `fault_code_totals`.

`fault_code_totals`: keys sorted ascending lexicographically.

Each `segments[]` element: `segment_id`, `integrity_pass`, `fault_codes`, `decoded_row_count`, `reconstruction_hash_hex`.

`fault_codes` sorted ascending lexicographically. Use `[]` when clean, never `null`.

## summary

```
{
  "segments_analyzed": int,
  "segments_passing": int,
  "segments_failing": int,
  "fault_code_totals": { "<fault_code>": int, ... }
}
```

Counts must reconcile with segment rows.

## segments

One object per `segment_01.json` through `segment_20.json`, sorted by `segment_id` ascending.
Ignore other `segment_*.json` files in the fixture directory.

`integrity_pass` is true only when `fault_codes` is empty.

### decoded_row_count

Decode every column independently (see SEGMENT_FORMAT.md). Then:

1. If no column produces a decoded value slice, set `decoded_row_count` to 0.
2. Otherwise sort decoded column names lexicographically and take the length of the first column's decoded slice.
3. If any other decoded column length differs, emit `COLUMN_ROW_MISMATCH` but still report the length from step 2.

Partial decode counts are expected. For example, dictionary indices may decode row-by-row even when an index is out of range (using the placeholder token `INVALID`), and RLE may expand to fewer rows than `row_count` when runs under-cover the segment. Use 0 only when decoding yields no rows at all, not when faults are present.

`reconstruction_hash_hex` is SHA256 hex over row-major decoded values: for each row index from 0 through `decoded_row_count - 1`, join `column=value` pairs for all columns sorted by name with `|`, then join rows with `;`. Use decoded string forms; null values encode as `NULL`. When `decoded_row_count` is 0, hash the empty string.

## Fault emission and decode fault suppression

Do **not** suppress secondary checks because an encoding fault is present. Run every applicable check against the decoded (possibly placeholder) values and emit every matching fault code as a distinct entry in `fault_codes`.

Examples of non-suppression:

- `DICT_INDEX_OOB` does not skip `STATS_DRIFT` or `PAGE_CORRUPTION` evaluated on the decoded tokens (including `INVALID`).
- `RLE_LENGTH_MISMATCH` does not skip statistics or page checksum checks on the expanded run values.
- Decode placeholders keep reconstruction and checksum pipelines running; they do not clear other fault codes.

Emit each fault code at most once per segment even if multiple columns trigger it.

## COLUMN_ROW_MISMATCH scope

Emit `COLUMN_ROW_MISMATCH` only when one of these holds:

1. **Cross-column decoded length clash**: after decoding, two or more columns have different decoded slice lengths (see `decoded_row_count` step 3).
2. **Plain payload length**: `encoding == "plain"` and `len(values) != row_count`.
3. **Delta payload length**: `encoding == "delta"` and `len(deltas) != row_count`.
4. **Bitpack payload length**: `encoding == "bitpack"` and `len(values) != row_count`.

Do **not** emit `COLUMN_ROW_MISMATCH` for:

- RLE expand length vs `row_count` (use `RLE_LENGTH_MISMATCH` only).
- Dictionary index out of range (use `DICT_INDEX_OOB` only).
- Dictionary incremental snapshot violations (use `DICT_INCREMENTAL_STALE` only).
- Null bitmap length errors (use `NULL_BITMAP_MISMATCH` only).

Dictionary `indices` length is the decoded row length for that column. If it differs from another column's decoded length, that is covered by rule 1 above, not by a separate dictionary-specific length fault.

## DICT_INCREMENTAL_STALE

When a dictionary column has `dictionary_revision > 0` and a non-empty `dictionary_snapshots` array:

1. Collect every snapshot with `revision < dictionary_revision`.
2. Let `allowed` be the minimum `len(dictionary)` among those prior snapshots. If no prior snapshot exists, `allowed` is `len(dictionary)` on the column itself.
3. Emit `DICT_INCREMENTAL_STALE` if any index in `indices` satisfies `index >= allowed`.

A stale index may still resolve against the current `dictionary` array (no `DICT_INDEX_OOB`). Emit `DICT_INDEX_OOB` only when `index < 0` or `index >= len(dictionary)` on the current column dictionary. Both codes may appear on the same segment when both conditions hold; neither suppresses the other.

## Fault codes

Emit only codes that apply. Standard codes:

`BITPACK_OVERFLOW`, `COLUMN_ROW_MISMATCH`, `DECODE_DIVERGENCE`, `DELTA_BASE_WRONG`,
`DICT_INCREMENTAL_STALE`, `DICT_INDEX_OOB`, `MERGE_ORDER_BROKEN`, `NULL_BITMAP_MISMATCH`,
`PAGE_CORRUPTION`, `PARALLEL_SLOT_COLLISION`, `PRUNE_COUNT_WRONG`, `ROW_GROUP_DRIFT`,
`RLE_LENGTH_MISMATCH`, `SCHEMA_EVOLUTION_GAP`, `STALE_METADATA`, `STATS_DRIFT`

## Bundled fixtures

The harness validates against unmodified `/app/fixtures/segment_01.json` through `segment_20.json`.
Do not edit bundled fixtures; the verifier recomputes SHA256 digests at test time.
