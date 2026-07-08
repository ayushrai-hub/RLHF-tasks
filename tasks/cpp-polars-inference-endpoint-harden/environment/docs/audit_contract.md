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

Digest and rounding rules are defined in `/app/docs/inference-operations-dossier.md` Sections 7–8 and Section 12. Digests truncate sha256 hex strings as specified there.

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
