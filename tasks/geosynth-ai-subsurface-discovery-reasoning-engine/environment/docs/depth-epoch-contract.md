# Depth epoch contract

depth-epoch reads the survey ingest catalog at /app/state/survey-ingest-catalog.json and writes the depth epoch ledger at /app/state/depth-epoch-ledger.json

## Global streaming segmentation

Segmentation is global, not per-block in isolation:

1. Sort all catalog traces by (recorded_at ascending, sample_id ascending).
2. Walk the sorted list once. Accumulate consecutive rows sharing the same block_id into one epoch bucket.
3. When block_id changes, close the current bucket and start a new bucket.
4. After the walk, close the final bucket.

Each epoch object includes:

- epoch_id: dep-NNN where NNN is a three-digit counter starting at 001 for the first closed bucket and incrementing by one for each subsequent bucket in encounter order.
- block_id: the exploration block for that bucket.
- sample_ids: sample_id values from the bucket in encounter order (same order they appeared in the global sorted walk).

The bundled survey yields three epochs (copper-belt-north, shale-margin-east, basalt-deep-west).

## epoch_digest field

depth-epoch-ledger.json top-level field epoch_digest is sha256 hex over sorted canonical lines:

```
epoch|<epoch_id>|<block_id>|<sample_count>
```

where sample_count is len(sample_ids) for that epoch.

## Bind fields

depth-epoch-ledger.json also records bound_catalog_digest copied from survey-ingest-catalog.json catalog_digest and bound_seq_ledger_digest copied from survey-seq-ledger.json survey_seq_ledger_digest after recomputing the seq ledger digest from the catalog.
