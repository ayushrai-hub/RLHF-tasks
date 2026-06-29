
# Sklearn pipeline column transform output contract

Authoritative shapes for CLI artifacts under `--out`. Split assignment, train ratios, export ordering, and transform block layout also appear in the long feature corpus under `/app/feature_corpus/`.

## CLI

- Binary: `java -Djava.library.path=/app/native -jar /app/java/build/libs/skct-pipeline-1.0.0.jar`
- Commands: `feature-ingest`, `column-transform-train`, `pipeline-export`, `parity-audit`
- Flags: `--bundle`, `--corpus`, `--out`
- Success sentinels (stdout): `FEATURE_INGEST_OK`, `COLUMN_TRANSFORM_OK`, `PIPELINE_EXPORT_OK`, `PARITY_AUDIT_OK`
- Native library: `column-transform-train`, `pipeline-export`, and `parity-audit` load `skct_kernel` from `-Djava.library.path`. Each exits non-zero when the library path is missing or unloadable.

Primary fixture paths:

| flag | path |
|------|------|
| `--bundle` | `/app/fixtures/bundles/pipeline_alpha_v3.json` |
| `--corpus` | `/app/feature_corpus/sklearn_pipeline_column_transform_corpus.md` |

Alternate bundled fixture: `/app/fixtures/bundles/pipeline_beta_v1.json` (same corpus; different split seed, train ratio, and export order).

## Generalization bundles

Train-only categorical vocabulary size depends on which city values land in the train split, not on the nine city labels present in the full bundle row set.

| bundle_id | split_seed | train_ratio | train rows | holdout rows | train city vocab |
| --- | --- | --- | --- | --- | --- |
| pipeline_alpha_v3 | 42 | 0.7 | 15 | 9 | 9 categories |
| pipeline_beta_v1 | 17 | 0.65 | 13 | 7 | 8 categories (AUS in holdout only) |
| pipeline_reseed_47 | 47 | 0.72 | 12 | 6 | 8 categories (SEA in holdout only) |

Holdout bundle `pipeline_reseed_47` is verifier-only; its corpus appendix overrides appear only in hidden verifier fixtures, not in the bundled primary corpus file.

Encoded block width equals the train-split city vocabulary length (one one-hot column per train-seen category). Score vector length is numeric block width plus encoded width plus passthrough width, ordered per corpus `export_order`.

## Corpus gate

- `--corpus` file length must be at least 500000 characters.
- Commands must exit non-zero when the gate fails.

## Split assignment

Assign train and holdout rows before computing any transform statistics.

```
payload = f"{row_id}:{split_seed}"
h = int.from_bytes(SHA256(payload.encode("utf-8"))[:4], "big") % 10000
row is train when h / 10000.0 < train_ratio, else holdout
```

## Column codec

First sixteen lowercase hex digits (first eight bytes) of SHA-256 of JSON array of column names in bundle column order (not sorted).

## Persistence layout

Format: `{prefix}:{slug}:{row_count}` where slug is feature lane with slashes replaced by dashes. Prefix is first four bytes of SHA-256(canonical persistence JSON) as little-endian u32 formatted eight lowercase hex digits. Canonical persistence JSON uses keys `bundle_id`, `lane`, `row_count` in that order with compact encoding.

## Column transform

Fit on train rows only. Numeric columns standardized with train mean and std. Categorical vocabulary for one-hot encoding is discovered from train rows only (not holdout or full bundle), using first-appearance order within the train split. Drop columns excluded from output. Passthrough columns appended as float64. Combined score vector concatenates blocks in corpus `export_order` (`numeric`, `encoded`, `passthrough`).

Sparse one-hot bits combine with float blocks via native `promoteSparseDtype(sparseVal, denseVal)` returning float64 promotion of the sparse indicator.

## Export digest

Shared by `export_digest` and `audit_digest`. Compact JSON uses UTF-8, no spaces, Gson field order preserved in object keys.

```
policy_json = compact_json({
  "bundle_id": <bundle_id>,
  "export_order": <corpus export_order list>,
  "transform_policy": {
    "numeric_columns": [...],
    "categorical_columns": [...],
    "drop_columns": [...],
    "passthrough_columns": [...]
  }
})
policy_sha256_raw_bytes = SHA256(policy_json.encode("utf-8")).digest()
blocks_json = compact_json(<blocks array>)
digest_hex = SHA256(blocks_json.encode("utf-8") + policy_sha256_raw_bytes).hexdigest()
```

`pipeline-export` blocks entries (one per export lane, in export order): `{block, dim, train_count}`. `dim` is 2 for `numeric`, 1 for `passthrough`, and the train-split categorical vocabulary length for `encoded`.

`parity-audit` blocks entries (one per export lane, in export order): `{block, flag_count}` where `flag_count` is the parity flag list length.

## Portable pipeline

`portable_pipeline.json` carries train-fit numeric stats, category maps, column roles, and export order for the C++ batch scorer consumed via JNI `scoreRow`.

## feature-ingest outputs

| file | requirement |
|------|-------------|
| feature_manifest.json | split manifest |

Required keys: `bundle_id`, `train_count`, `test_count`, `column_codec`, `sample_persistence_id`, `policy` with `train_ratio`, `export_order`.

## column-transform-train outputs

| file | requirement |
|------|-------------|
| transform_report.json | train-only score vectors |

Required keys: `bundle_id`, `train_count`, `score_vectors` array with `row_id` and `score_vector` for each train row using train-only fit and native dtype promotion.

## pipeline-export outputs

| file | requirement |
|------|-------------|
| pipeline_registry.json | registry digest |
| portable_pipeline.json | portable serializer payload |

Required registry keys: `bundle_id`, `export_order`, `export_digest`, `blocks`. Export order follows corpus policy ingest order not lexical sort.

## parity-audit outputs

| file | requirement |
|------|-------------|
| parity_audit.json | Java transform vs C++ batch scorer |

Required keys: `bundle_id`, `parity_flags` array of `{row_id, max_delta}` for train rows where Java score vectors differ from C++ batch scorer, `audit_digest` as the export digest over the audit `blocks` array.

## Protected artifacts

Do not modify `/app/fixtures/` or `/app/scripts/run_integration_tests.sh`.
