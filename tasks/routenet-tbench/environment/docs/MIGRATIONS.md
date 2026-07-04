# Migration log

The Postgres schema is small and the seed loader (`scripts/load-seed.js`)
rebuilds it from scratch the first time `scripts/start-system.sh` runs. This file records the design
history that led to the current shape so that the split semantics in
`SCHEMA.md` are not surprising.

## v1 (initial)

- `nodes (id, label)` and `edges (u, v)`.
- Negatives were sampled uniformly at random from the complement of the edge
  set. Validation AUC was useful in principle but uninformative in practice
  because random pairs are trivially separable.

## v2 (add splits column)

- Added `edges.split TEXT NOT NULL` with values in `{train, val, test}`.
- Updated training code to filter on `split = 'train'` and to score on the
  `val` split. AUC numbers became meaningful but high-variance across seeds.

## v3 (add splits summary table)

- Added the `splits` bookkeeping table to record per-split counts. This is
  informational only - the authoritative split is the `split` column on
  `edges`.
- Introduced an on-disk snapshot at `data/snapshot.json`, intended as a
  cache so the sampler did not have to round-trip to Postgres. The split
  assignment in the snapshot was hand-copied from the database at the time
  it was generated.

## v4 (rebalance splits, current)

- Re-tuned the `split` assignment on `edges` so the train subgraph is
  connected from any starting node within at most a few hops. The snapshot
  file was not regenerated.
- This is the state the repaired sampler should target. The authoritative
  splits are the ones in `edges.split`, not the ones in
  `data/snapshot.json`.
