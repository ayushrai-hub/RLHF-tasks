# k7 trace report

## Output

`/app/output/k7_trace.json`

Root fields: `rows` (array), `chain_fingerprint` (64-char lowercase hex sha256).

## Row schema

| Field | Type | Notes |
|-------|------|-------|
| `scenario` | int | Replay case index |
| `view` | string | `spool`, `drift`, or `live` |
| `principal` | string | Active principal |
| `label` | string | Profile label |
| `generation` | int | Active-ward generation |
| `action_code` | int | `0` nominal; `6` readopt; `7` mismatch; `9` live deny |

Multiple rows per view per scenario are allowed (primary active row plus transition outcomes).

## chain_fingerprint

Sort rows by `scenario,view,principal,label,generation` (lexicographic lines, trailing newline). `chain_fingerprint` is sha256 hex of that UTF-8 text.

## Fixtures

Scenarios s0–s4 under `/app/cases/seq/sN` with `a0.tree`, `b0.tree`, `i0.frag`. Tree lines use `ward=active` with `principal`, `label`, `gen`, optional `action`. Each write phase adds one to active-ward `gen` before verify.

`i0.frag` supplies `epoch=` and `digest=`. Ward files under `/app/replay-state/store/` embed the fragment digest in the filename key material.

## WAL

Path: `/app/replay-state/wal/chain.wal`. Each line: JSON, tab, CRC32 of `scenario:phase:ward_gen:frame_gen:seq` (zlib polynomial).

Scenarios 1–4: first phase `bust`, then `success`. `seq` strictly increases chain-wide. Full s0–s4 chain: ≥25 records.

## Checkpoint

`/app/replay-state/checkpoint.json`: `last_scenario`, `wal_seq`, `order_seal`, `valid`.

Recompute `order_seal` by walking CRC-valid WAL lines in order. Reset per-scenario `saw_bust` when `scenario` changes. On `bust`, set `saw_bust`. On `success` after `bust`, add `0xBEEF` (64-bit wrap). On `success` without prior `bust` in scenario, `seal = (seal * 31 + seq) mod 2^64`.

`valid` is `true` only when phase order, CRC integrity, and stored `order_seal` match recomputation. `k7_z2` refuses emit on drift; `k7_recover` rebuilds from WAL.

## Cross-view

Scenarios 1–4: spool and live active generations match except scenario 3 live deny (`action_code` 9). Spool and drift generations match for the same principal.

Scenario 1: after reconciliation, no live row has `action_code` 7 (`false` for mismatch on that view).

Scenario 2: ≥2 live rows; the transition outcome row (not the primary) always has non-zero `action_code` even when sync aligns primary generations.

Scenario 3: ≥2 live rows; revocation deny uses `action_code` 9.

Scenario 4: ≥2 live rows; readopt uses `action_code` 6 when include epoch advances.

When live generation exceeds drift, drift rows may carry non-zero `action_code`.

Partial replay through scenario 3 omits scenario 4 rows until case four is replayed; completing scenario 4 changes `chain_fingerprint`.

Full reconciled chain: ≥18 rows.

## Sync

During `sync` on scenarios 1–4, live ward generation must track spool ward generation (WAL `ward_gen` and `frame_gen` align on sync records).

## Idempotency

Repeated `k7_invoke` on unchanged fixtures yields identical `epoch_N.json` and valid WAL lines. Repeated `k7_recover` / `k7_z2` on unchanged state yields identical checkpoint and fingerprint.

## Metrics

`/app/replay-state/last_metrics.json`: `store_hits`, `lane_attempts`, `leaf_epoch` (matches scenario 4 include epoch after full chain).
