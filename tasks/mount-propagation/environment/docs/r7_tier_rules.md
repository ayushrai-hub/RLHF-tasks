# R7 matrix record (field glossary)

Records are written to `/app/output/r7_matrix_record.json` by `ctl_r7`.

## Top-level fields

- `scenario` — active case slug from the case JSON file.
- `chain_hex` — lowercase hex digest over exported row material; verify with `/usr/local/bin/chain_ref` on the `rows` array JSON. Row-order permutations must not change the digest.
- `rows` — one export row per entity listed in the active case roster.
- `observations` — phase/cycle trace emitted during reconcile passes; multi-cycle runs accumulate entries. Observations may carry `branch` from the active segment.
- `evidence` — reconcile cells keyed by entity-oriented ids with integer `phase` stamps. Multi-cycle runs accumulate entries without deduplicating by id across cycles.

## Row fields

Each row carries `entity`, tri-form keys, `marker`, `book_cell`, and compact-pass `wave`. The `path_key` field means the path-style key `p/{entity}`. The `uri_key` field means the URI-style key `u://{entity}`. The `ref_key` field means the opaque ref `r:{entity}`. Exported `book_cell` values must agree with active segment replay for the case segment and must not endswith `_cache_stale`. Exported `marker` values must agree with checkpoint seeds for the case checkpoint through compact pass two with `wave` equal to 2. Exported markers must not startswith `compact_wave_` or internal `rk_` run-stamp aliases. Exported book cells must not retain cache-local suffix decoration. These negative constraints are part of the public export contract, not optional hygiene checks.

## Observation counts

Two-cycle reconcile cases emit at least 8 phase observations across both cycles. Three-cycle tandem cases emit at least 12 phase observations across all cycles.

## Evidence retention

Multi-cycle reconcile must retain evidence across cycles. Two-cycle cases should keep at least 4 evidence entries per entity with both phase one and phase two represented. Three-cycle cases should keep at least 4 evidence entries per entity with both low phases represented. Tandem three-cycle evidence must retain distinct `wave1` and `wave2` payload tags per entity across compact waves.

## Correlation sources

Segment cells load from `fixtures/sidecars/` during recover. Checkpoint seeds load from `data/checkpoints/`. Bind rosters live in `data/propagation/bind_scope.toml` keyed by checkpoint stem aligned with `cp_blob_<stem>.bin`. Persisted lane state is written under `state/mp_lane.json` with per-slug `committed_gen`, `active_slug`, `by_slug`, and `wal_obs` keys. Each export must include every entity listed in the active case roster. Switching scenario slugs in one process must not leak prior slug roster, stamp, cell material, or `wal_replay` observations into later exports. Recover passes must not resurrect book cells from earlier scenarios when entity rosters overlap. A slug chain ending on a case must match the byte-identical export from running that case in isolation after the same chain priming. Repeat runs of the same slug must advance `committed_gen` monotonically in lane state. Final exports must not contain `wal_replay` phase observations. After a slug pivot, persisted `wal_obs` must not retain observation keys from prior slugs before the next export commits. Malformed or truncated lane-state JSON must not block later isolated runs from producing the same bytes as a clean-state invoke. Deeper pass behavior is split across the wired import graph — correlate fragments, fixtures, lane state, and `chain_ref` rather than treating any one file as sufficient.
