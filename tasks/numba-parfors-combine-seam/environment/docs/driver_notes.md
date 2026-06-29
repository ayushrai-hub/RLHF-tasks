# Array reduction replay driver notes

## Rebuild after source edits

```bash
cd /app/environment
/usr/local/cargo/bin/cargo build --release --locked
```

## r8_run

```bash
/app/environment/tools/r8_run --scenario N
```

Replay one scenario (`N` from 0 through 4). Caches rows under `/app/replay-state/epoch_N.json`.

## r8_emit

```bash
/app/environment/tools/r8_emit --out /app/output/r8_trace.json
```

Emit the cross-view trace when checkpoint state is valid. Emit re-reads every physical line in `/app/replay-state/wal/chain.wal` and rejects output when any line CRC disagrees with recomputation per `r8_contract.md`.

## r8_recover

```bash
/app/environment/tools/r8_recover
```

Rebuild checkpoint validity from the append log chain.

## Cases

Scenario fixtures live under `/app/cases/seq/s0` through `/app/cases/seq/s4`. Each scenario directory ships `a0.arr`, `b0.arr`, and `i0.tab` snapshots.

Working state lives under `/app/replay-state`.

## r8_sample

```bash
/app/environment/tools/r8_sample
/app/environment/tools/r8_sample --scenario N
```

Print JSON samples of reduce, promote, and live generations per scenario epoch cache.
