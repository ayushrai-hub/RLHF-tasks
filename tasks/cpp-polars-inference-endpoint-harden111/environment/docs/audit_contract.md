# Batch audit contract

`/app/output/batch_audit.json` is the regression snapshot for bundled scoring rows.

## Root fields

| Field | Type | Notes |
|-------|------|-------|
| api_version | string | always `"1"` |
| policy_seq | string | 16-char hex digest of ratified policy JSON |
| lock_digest | string | 16-char hex digest of `polars==<pin>` |
| accepted | integer | rows scored with `status` `ok` |
| rejected | integer | rows with `status` `rejected` |
| scores | array | sorted ascending by `row_id` |

## Score row fields

| Field | Type | Notes |
|-------|------|-------|
| row_id | string | request row identifier |
| score | number or null | rounded ridge score when `ok` |
| feature_digest | string or null | 16-char hex when `ok` |
| status | string | `ok` or `rejected` |

## feature_digest byte contract

`feature_digest` is the first 16 lowercase hex characters of SHA-256 over the UTF-8 bytes of a compact feature JSON object for that row:

1. Include every feature key the sidecar emits: `age_ff`, `tenure_ff`, all four `region_*` one-hot keys, and all three `channel_*` one-hot keys. Inactive one-hot keys remain present with value `0.0` (do not omit zeros).
2. Sort object keys in ascending lexicographic order before serialization.
3. Render each numeric value with exactly six digits after the decimal point (fixed six-decimal form, e.g. `1.000000` and `0.000000`), after rounding to six decimals.
4. Emit compact JSON with no spaces: `{"key":0.123456,"other":1.000000}` (double-quoted keys, comma-separated members, surrounding braces).

`policy_seq` and `lock_digest` truncation rules, ridge rounding, and ratified policy values are defined in `/app/docs/inference-operations-dossier.md` Sections 7–8 and Section 12.

## Ridge weights

Scoring loads `/app/environment/config/model_weights.json`, including `bias` and per-feature coefficients aligned with sidecar feature keys.

## Policy JSON keys for policy_seq

| Key | Ratified value |
|-----|----------------|
| max_batch_rows | 32 |
| null_fill | forward |
| unknown_category | reject |
| polars_pin | 1.12.0 |
| score_precision | 6 |
