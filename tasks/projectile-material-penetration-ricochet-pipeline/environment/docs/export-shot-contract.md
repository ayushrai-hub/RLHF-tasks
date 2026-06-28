# Export shot contract

Production export uses a **two-step CLI pipeline**. Do not rely on `ballctl simulate-shot` for audit JSON — it is a legacy shortcut that skips staged export rules.

## Step 1 — integrate-shot

```bash
ballctl integrate-shot \
  --stack /app/fixtures/stacks/multi-layer.json \
  --materials /app/fixtures/materials/catalog.json \
  --velocity 0,0,-420 \
  --energy 3200 \
  --seed 42
```

Runs trajectory integration, assigns `replay_seq` per `/app/docs/replay-epoch.md`, and writes **`/app/state/shot-snapshot.json`**. No export JSON is produced.

## Step 2 — export-shot

```bash
ballctl export-shot --export /app/output/shot.json
```

Reads the staged snapshot from disk and emits shot JSON per `/app/docs/export-schema.md`, including `trace_digest`.

Batch runs (`simulate-batch`) must perform integrate + export for every hit before tick rollup per `/app/docs/batch-contract.md`.
