# verify-transfer-runs

Batch relay driver for supervised bulk transfers. Processes every `pack_k*.json` fixture under a fixtures directory, maintains byte ledgers across reader recycles, and writes run records plus sidecar traces used by downstream audit. Module-level source under `/app/environment` must be corrected; the verifier rebuilds the driver from that tree before checking outputs.

## Build and run

```bash
cd /app/environment && go build -o /app/bin/verify-transfer-runs /app/environment/cmd/verify-transfer-runs
```

```bash
/app/bin/verify-transfer-runs \
  --fixtures-dir /app/data/fixtures \
  --out /app/output/run_records.json \
  --trace-out /app/output/ledger_trace.jsonl \
  --journal-out /app/output/span_journal.jsonl \
  --manifest-out /app/output/run_manifest.jsonl \
  --audit-out /app/output/run_audit.jsonl \
  --ledger-state /app/output/run_ledger.state
```

Platform verification reruns this command; pytest flags such as `--ctrf` are harness-only. Independent digest checks may recompute sha256 material with `openssl dgst -sha256`.

## Fixture packs

Each JSON pack includes `sink_mode` (`wrap` or `redirect`), `pipe_cap`, and `events` with `kind` in `seed`, `wave`, `recycle`.

Bundled stems include `pack_k1` through `pack_k8`. Runtime-added stems such as `pack_k7` follow the same discovery rule: every `pack_k*.json` present under the fixtures directory before a run appears in all outputs.

Per-pack `observed_bytes` equals the sum of all `wave` `bytes`, including waves before and after recycles. After recycle, `writer_epoch` equals the new `reader_epoch`.

## Slice policy config

`/app/environment/config/base.toml` and `/app/environment/config/overlay.toml` each define `[slice] chunk_divisor` (positive integer). Merge loads overlay first, then applies base keys **only for keys absent from overlay** — overlay wins on conflict.

Effective chunk size for wrap-mode slicing is `pipe_cap / chunk_divisor` (minimum 512 bytes). On wrap fixtures, plan every `wave` into segments of at most that chunk size and emit one trace `wave_slice` row per segment until the wave is fully observed. Redirect fixtures do not emit `wave_slice` rows.

## Resume offset store

`/app/state/resume.offset` may contain JSON `{fixture_label, reader_epoch, observed_bytes}`. At fixture start, add `observed_bytes` to the byte ledger **only when** both `fixture_label` and `reader_epoch` match the fixture's current seed epoch. The image seeds a stale example targeting `pack_k3` with a mismatched epoch; that preload must not change totals for the bundled `pack_k3` run.

## Segment cache

`/app/state/segment.cache.json` maps cache keys to `{observed_bytes, reader_epoch}`. Keys are `fixture_label|reader_epoch`. Before processing waves for a fixture, do not reuse cached spans unless the key matches the active reader epoch. Update the cache entry after each fixture completes.

## run_records.json

Top-level JSON with a `runs` array. Each row has `fixture_label`, `writer_epoch`, `reader_epoch`, `byte_span` (`start_offset`, `end_offset`, `observed_bytes`), `fingerprint` (32 hex chars), and `checkpoint_seal` (32 hex chars).

`fingerprint` is sha256 over `writer|reader|start|end|observed` (first 32 hex chars).

`checkpoint_seal` is sha256 over `journal_tail|fixture_label|observed_bytes`, where `journal_tail` is the last journal `link` for that fixture.

## ledger_trace.jsonl

JSON Lines with `fixture_label`, `phase`, `observed`, `pending`, `writer_epoch`, `reader_epoch`, and `span_mix`. Phases include `seed`, `wave_slice`, `wave_end`, `recycle_before`, and `recycle_after`.

On wrap fixtures, plan each `wave` into segments of at most `pipe_cap / chunk_divisor` bytes (minimum 512) and emit one `wave_slice` row per segment until the wave is fully observed. At each `wave_slice`, `observed` is the portion of that wave's bytes already committed and `pending` is the portion still outstanding; `observed + pending` equals that wave's `bytes` on every slice, the running total is non-decreasing across successive `wave_slice` rows for the same wave, and the final slice reaches the wave byte count. Each completed wave ends with a `wave_end` row where `pending` is zero and `observed` is the fixture cumulative total. `recycle_before` rows flush outstanding bytes (`pending` zero) before an epoch change; the matching `recycle_after` row carries the same `observed` with `pending` zero.

## span_journal.jsonl

Checkpoint phases in run order with `seq`, `fixture_label`, `phase`, `observed`, `pending`, and `link`. The link is the first 32 hex chars of sha256 over `prev_link|seq|fixture_label|phase|observed|pending`, chaining from `genesis`. Journal `seq` values increase by one across the entire run with no gaps or resets between fixtures.

## run_manifest.jsonl

One line per fixture with `fixture_label`, `journal_tail`, `trace_lines`, `wave_slices`, and `manifest_seal`. `manifest_seal` is sha256 over `journal_tail|trace_lines|wave_slices|observed_bytes` for the fixture's final observed total.

## run_audit.jsonl

After primary outputs are written, the binary performs a delayed audit pass rereading report, journal, and manifest from disk. One line per fixture with `fixture_label`, `journal_tail`, `manifest_seal`, `checkpoint_seal`, and `audit_seal`. `audit_seal` is sha256 over `journal_tail|manifest_seal|checkpoint_seal`.

## run_ledger.state

Persists across verifier invocations as JSON with `run_count`, `prev_audit_tail`, and `chain_seal`. Each successful verify increments `run_count`, sets `prev_audit_tail` to that run's final `audit_seal` (the last audit line's seal), and sets `chain_seal` to sha256 over `prior_prev_audit_tail|final_audit_seal|run_count`, where `prior_prev_audit_tail` is the previous file's `prev_audit_tail` (or `genesis` on the first run). Tampered ledger values are replaced on verify along with the other outputs.

Two consecutive verify runs with the same fixtures must produce identical journal link sequences and identical audit seal sequences.
