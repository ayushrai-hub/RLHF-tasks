# vendor_audit.json schema

The simulator writes a JSON object report with:

- `config_id`, `seed`, `view_mode`, `panel_id`, `stage_width`, `max_period`
- `flags`: `multi_stage`, `strict_stage_sort`, `deferred_rollout`, `track_exposure` (booleans)
- `accounts`: vendor limit rows from the active panel fixture as `{vendor_id, vendor_graph_cap}` pairs
- `lines`: per-invoice outcomes (sorted by `invoice_id`)
- `summary`: aggregate tallies and fingerprint
- `ticks`: per-period stage snapshots

## Invoice rows (`lines`)

Use these exact keys on every invoice row — **not** `period_index` or `stage_index`:

- `invoice_id` (string)
- `vendor_id` (string)
- `period` (int): funnel period on the invoice row
- `stage` (int): stage index within the period on the invoice row
- `weight_pts` (int)
- `bind_slot` (int): monotonic binding index for accepted rows; `-1` when rejected
- `status` (string): `accepted` or `rejected`
- `phantom_pts` (int): portion of the invoice that exceeded the vendor cap after binding

## Summary

- `accepted_count` (int)
- `rejected_count` (int)
- `phantom_event_count` (int): accepted rows with `phantom_pts > 0`
- `phantom_spend_total` (int): sum of `phantom_pts` across accepted rows
- `vendor_fingerprint` (string): 64-character lowercase SHA-256 hex digest over ordered `invoice_id:bind_slot` pairs for accepted rows
- `restore_applied_count` (int): times a period snapshot was restored during `period_failover` runs
- `replay_periods_count` (int): periods replayed after restore before continuing
- `restore_trim_count` (int): invoice rows trimmed while merging a restored snapshot
- `replay_scheduled_count` (int): scheduled replay span width at the failover boundary (`failover_period` minus the captured snapshot `settled_period`)
- On the bundled `period_failover.json` profile, a correct run reports `replay_scheduled_count` of `1`, `replay_periods_count` of `1`, and `restore_applied_count` of `1`; see `fixture_layout.md`

## Period snapshots (`ticks`)

Each tick row uses `period_index` for the snapshot period counter (distinct from invoice-row `period`):

- `period_index` (int)
- `stage_digest` (string): SHA-256 hex over sorted `vendor_id:committed_pts:pending_pts` triples
- `vendor_snaps`: array of `{vendor_id, committed_pts, pending_pts}` sorted by `vendor_id`

After period-boundary settlement on vendor_graph runs with `deferred_rollout`, every `vendor_snaps` row in a completed period tick should show `pending_pts` of `0`.

## Warm checkpoints

Profiles may set optional `checkpoint_out` (write path) or `warm_checkpoint` (read path). Checkpoint JSON fields:

- `last_period_index` (int): last completed snapshot period
- `committed_pts` (object): map of vendor id to committed weight points
- `pending_pts` (object): map of vendor id to pending weight points
- `next_bind_slot` (int): next bind slot cursor
- `rejected_count` (int): rejected invoice tally carried forward
- `lines` (array): invoice rows emitted before the checkpoint boundary
- `ticks` (array): period snapshots through `last_period_index` (length is exactly `last_period_index + 1`)
- `state_digest` (string): SHA-256 hex over sorted `vendor_id:committed_pts` pairs

A warm run reloads that ledger and continues from the next period index; the merged audit must match a single cold run over the full window.

On a correct north `burst.json` prefix checkpoint at `last_period_index` `2`, `committed_pts` maps to `vendor-acme` `800` and `vendor-beta` `400`, matching period-index `2` in the full-run trajectory table in `fixture_layout.md`. At `period_index` `7` on the full burst run, `vendor-acme` `committed_pts` remains `1000`.

## View modes

- `line_item`: stages within a period are processed in `(stage, invoice_id)` order; each accept flushes that vendor before the next stage runs.
- `vendor_graph`: all stages in a period are accepted against the same visibility snapshot, then pending weight points roll up at period end when `deferred_rollout` is enabled.

## Parity expectations

When comparing **line_item** to **vendor_graph** with the same seed, panel, stage geometry, and flags on a correct run:

- Every manifest invoice id for that panel must appear exactly once in `lines`.
- All five `summary` tallies must match between modes.
- On a correct run, `phantom_event_count` and `phantom_spend_total` are each `0`.
- `vendor_fingerprint` must match.
- For each `invoice_id`, `bind_slot`, `status`, and `phantom_pts` must match between modes.
- For each matching `period_index`, `stage_digest` and every `vendor_snaps` row must match between modes.
- `bind_slot` values are unique among accepted rows and strictly increase in apply order `(period, stage, invoice_id)`; the first accepted row uses bind slot `1` with no gaps in the accepted sequence.
- On a correct run, each period snapshot keeps `committed_pts + pending_pts` at or below that vendor's `vendor_graph_cap`.
- For each vendor id, `committed_pts` in `vendor_snaps` never decreases as `period_index` increases.
- `lines` are sorted by `invoice_id`; each period row's `vendor_snaps` are sorted by `vendor_id`.
- `ticks` contains exactly `max_period + 1` rows with `period_index` values `0` through `max_period`.
- For accepted rows, `0 <= phantom_pts <= weight_pts`; rejected rows keep `phantom_pts` at `0`.
- `summary` tallies match row-level accepted/rejected counts and the sum of `phantom_pts` on accepted rows.
- `report["summary"]["accepted_count"] + report["summary"]["rejected_count"]` equals the manifest invoice count for the active panel fixture (each manifest id appears exactly once in `lines`).
- Top-level metadata (`config_id`, `seed`, `view_mode`, `panel_id`, `stage_width`, `max_period`, `flags`) matches the profile JSON used for the run.

Digest helpers use pipe-separated parts hashed with SHA-256 (`sha256`), lowercase hex.

## Verifier expectations

- Run every profile listed in `operations.md` under both **line_item** and **vendor_graph** overrides and require full row/summary/period parity plus zero phantom tallies.
- On vendor_graph runs: recompute `vendor_fingerprint` and each `stage_digest`; enforce summary/row tally consistency; keep period snapshots within vendor caps; bound accepted `phantom_pts` by row `weight_pts`; require `ticks` length `max_period + 1` with contiguous `period_index` values; echo profile metadata and `flags` in the report.
- Exercise warm-checkpoint continuation, north/south rejection triples, and `stage_width` filtering documented in `fixture_layout.md`, including `delay_ticks.json` geometry and profiles with `deferred_rollout`, `strict_stage_sort`, `track_exposure`, or `multi_stage` disabled while still requiring mode parity.

For the north panel with default flags, period 0 carries three concurrent stages for `vendor-acme` at 400 weight points each against a 1000-point cap. A correct run rejects the third invoice in both view modes and keeps `phantom_spend_total` at `0`.
