# k7 driver notes

## Build

```bash
cd /app/environment
/usr/local/cargo/bin/cargo build --release --locked
```

Rebuild after any source change before replay.

## k7_invoke

```bash
/app/environment/tools/k7_invoke --scenario N
```

Replays one scenario (`N` = 0 … 4). Writes row cache to `/app/replay-state/epoch_N.json` and appends WAL records.

## k7_z2

```bash
/app/environment/tools/k7_z2 --out /app/output/k7_trace.json
```

Folds epoch caches into the cross-view report. Requires valid checkpoint and intact WAL CRC on every physical line in `/app/replay-state/wal/chain.wal`.

## k7_recover

```bash
/app/environment/tools/k7_recover
```

Recomputes checkpoint metadata from the WAL per `k7_contract.md`.

## Typical workflow

```bash
for n in 0 1 2 3 4; do /app/environment/tools/k7_invoke --scenario $n; done
/app/environment/tools/k7_z2 --out /app/output/k7_trace.json
```

If emit fails on checkpoint drift, run `k7_recover` and retry `k7_z2`.

## Paths

| Path | Purpose |
|------|---------|
| `/app/cases/seq/s0` … `s4` | Scenario fixtures (`a0.tree`, `b0.tree`, `i0.frag`) |
| `/app/replay-state/epoch_N.json` | Per-scenario row cache |
| `/app/replay-state/wal/chain.wal` | Durable append log |
| `/app/replay-state/checkpoint.json` | Checkpoint seal |
| `/app/replay-state/store/` | Hold-store ward files |
| `/app/replay-state/last_metrics.json` | Runtime counters |
| `/app/output/k7_trace.json` | Emitted trace report |

Contract details: `k7_contract.md`.
