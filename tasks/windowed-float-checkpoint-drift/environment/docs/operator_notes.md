# Operator notes

The `stream-stats` binary is installed at `/usr/local/bin/stream-stats`. Sources live under `/app/environment`.

## Build

After editing sources under `/app/environment`, rebuild and reinstall before running `stream-stats`:

```
bash /app/environment/scripts/build_stats.sh
```

That script compiles the release binary and installs it to `/usr/local/bin/stream-stats`. Platform checks invoke that installed path directly and do not rebuild automatically, so a stale install will keep serving pre-edit behavior.

## Run

```
stream-stats run --profile cold --seed <n>
```

Ingests the fixed dataset for the seed from `fixtures/` and emits public artifacts under `/app/output/`. A durable partial frame is written under `/app/var/dur_frame.bin` at the midpoint boundary. The frame carries a per-seed `frame_gen` and a sealed merge `plan` (branch ids ordered by combine_rank). Tail rows are appended to `/app/var/wal_segment.jsonl` as JSON objects `{seal_gen, event}` where `seal_gen` equals the active `frame_gen`. A generation fence journal is appended at `/app/var/fence_journal.jsonl` as JSON objects `{seed, frame_gen, seal_kind}` recording the active seal for that seed. A full run replaces the WAL segment and fence journal for a clean seal generation.

## Continue

```
stream-stats resume --from-checkpoint <path> --seed <n>
```

Hydrates the durable partial frame at `<path>` and continues ingestion for the same seed. Reuse slots persist under `/app/var/reuse_state.json` between continue invocations, including the advancement epoch counter, `frame_gen`, and `drain_wm`. The persisted epoch must increase by at least one on every continue invocation with no new fixture rows. After each continue, `drain_wm` and the stored `frame_gen` must equal the hydrated frame's `frame_gen`.

Tail rows appended during the preceding full run are replayed from `/app/var/wal_segment.jsonl` before the continue profile merges branch partials. Replay scans the segment in file order, skips malformed JSON lines without aborting, keeps only records whose `seal_gen` equals the active frame generation, then sorts the surviving rows by event time and sequence before ingestion. Salvage must work when the malformed line appears at the start, middle, or end of the segment, and when multiple malformed lines appear in one segment. Rows sealed under a different generation must not affect published metrics.

A full run for one seed replaces `/app/var/dur_frame.bin`, `/app/var/wal_segment.jsonl`, and related durable files. A continued run for seed *n* requires a preceding full run for the same seed *n* in the current durable-state generation, even if another seed's full run ran in between.

## Seeds

Even seeds load `fixtures/events_seed_a.tsv`. Odd seeds load `fixtures/events_seed_b.tsv`, which includes out-of-order arrivals that share span boundaries with earlier rows.

Profile metadata in `config/profiles.toml` documents span width and fold thread counts only; it does not override seed fixture selection.

Platform verifier pytest runs may pass harness-only flags such as `--ctrf` for structured logging; those flags are not part of the task CLI contract.

## Published sum and branch totals

The published `sum` metric is the direct arithmetic sum of raw event `value` fields from the ingested fixture row set. It must not be taken from the running fold accumulator's partial-sum field, which may diverge under alternate reduction order.

`branch_totals` and `global_total` are derived from pre-merge per-branch partial sums (each branch's live accumulator sum after head hydrate, WAL late overlay, and live-tail integration). On a healthy run, `global_total` matches the published `sum` and the sum of `branch_totals[].total` within the mean absolute band (`1e-12`). Narrowing partials on the durable frame, dropping the sealed plan, or applying the wrong WAL generation breaks this agreement on continued runs even when per-branch health digests still match.

## Tolerance bands

- `sum`, `count`: exact integer equality
- `mean`: absolute epsilon `1e-12`
- `var`, `stddev`: relative epsilon `1e-9` against the reference replay
- `p50`, `p95`, `p99`: absolute epsilon `1e-8` on the quantile value
- `cross_partition_total`: `global_total` must exactly equal the sum of `branch_totals[].total`

## Tail reservoir

Published `p50`, `p95`, and `p99` values are computed from a bounded per-lane reservoir holding at most 12 `(ev_time, seq, value)` tuples. Reservoir merges during branch combine must retain the newest tuples by event time and sequence. Quantile values are taken from the sorted reservoir values.

## Output schemas

Regenerated artifacts (verifier deletes before check): `/app/output/run_report.json`, `/app/output/merge_trace.jsonl`, `/app/output/resume_diff_summary.json`.

Run report JSON fields: `seed` (int), `profile` (string), `metrics` (object mapping metric name to `{value, tol_class}`), `global_total` (float), `branch_totals` (array of `{branch_id, total}`), `observed_merge_steps` (int), `frame_gen` (int), `plan_digest` (string). No fields ending in `_ok`, `_valid`, or `_passes`.

`plan_digest` is a 16-character lowercase hex string. Start with `h = 0xcbf29ce484222325`. For each branch id in the sealed plan, for each UTF-8 byte `b` set `h = (h XOR b) * 0x100000001b3` (mod 2^64), then set `h = (h XOR 0xff) * 0x100000001b3` (mod 2^64). Format `h` as 16 zero-padded lowercase hex digits.

Trace JSONL rows: `step` (int), `left_branch` (string), `right_branch` (string), `combine_rank` (int). Each branch partial carries `combine_rank = hash(part_id) * 1_000_000_000 + max_event_sequence`, where `hash` starts at 0 and for each byte `b` of the UTF-8 partition id updates `h = (h * 131 + b) mod 2^64`. Parallel merge follows the sealed plan order, repeatedly pairs the two lowest live ranks, and continues until one partial remains. Each emitted trace row's `combine_rank` is the greater of the two branch partial ranks merged at that step, floored by the previous emitted rank so the sequence is monotonic non-decreasing. The run report field `observed_merge_steps` must equal the number of rows emitted in `merge_trace.jsonl` for that profile.

Resume diff JSON fields: `metric_deltas` (array of `{name, cold, warm, abs_delta, rel_delta, within_band}`), `ordering_violations` (int), `max_combine_rank` (int), `frame_gen` (int), `seal_gen` (int), `drain_wm` (int), `plan_digest` (string). The `max_combine_rank` value must equal the peak emitted trace `combine_rank` on the continued run and must match the full-run peak for the same seed. On a healthy continue, `frame_gen`, `seal_gen`, and `drain_wm` must all equal the active frame generation, and `plan_digest` must match the run report. `seal_gen` is taken from the fence journal entry for the active seed when present, otherwise from the WAL seal peak; both the fence journal's latest `frame_gen` for that seed and the WAL seal peak must equal the active frame generation.

## Merge trace parity

Full and continued runs for the same seed must emit the same multiset of merged branch-id pairs in `merge_trace.jsonl`. Pair identity ignores step order: normalize each row to `(min(left_branch, right_branch), max(left_branch, right_branch))` and compare sorted multisets between profiles.

A full-then-continue-then-full-then-continue cycle for one seed must reproduce the same published metrics, plan_digest, combine_rank sequence, branch-pair multiset, and trace step numbering as the initial full run for that seed. After another seed's full run overwrites durable files, a continued run for the original seed must match that seed's latest full run on metrics, plan_digest, frame_gen, and trace invariants.

Per-branch health digests logged during frame persistence may agree across profiles while global run-report metrics diverge when durable partials lose precision.
