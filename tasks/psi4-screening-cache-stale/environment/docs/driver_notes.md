# Driver notes

Working directory is `/app`.

## Rebuild

```bash
cd /app/environment && cmake -S . -B build && cmake --build build --parallel
```

## Case snapshot anchors

Each replay case under `/app/cases/seq/sN/` ships frozen generation anchors in snapshot files.

- `screen_gen` in `a0.scn` means the screen-view generation epoch tag expected after a correct replay.
- `swap_gen` in `b0.swp` means the swap-view generation epoch tag expected after a correct replay.
- `live_gen` in `a0.scn` means the live-view generation floor for scenarios that emit live rows.

Anchor lines use `fieldname=integer` (for example `screen_gen=1`).

Emitted epoch `generation` fields must match these anchors where tests compare fixture-grounded rows.

## p7_run

```bash
/app/environment/tools/p7_run --cold
/app/environment/tools/p7_run --scenario 0
/app/environment/tools/p7_run --cold --scenario 0
/app/environment/tools/p7_run --scenario 1
/app/environment/tools/p7_run --scenario 4
```

## p7_emit

```bash
/app/environment/tools/p7_emit --out /app/output/p7_trace.json
```

## p7_recover

```bash
/app/environment/tools/p7_recover
```

## p7_inspect

```bash
/app/environment/tools/p7_inspect
```
