# Export schema

## simulate-shot

```json
{
  "stack": "multi-layer",
  "seed": 42,
  "path_ledger_m": 0.012,
  "exit_energy_j": 2492.8,
  "penetrated": true,
  "layers": [ ... ],
  "ricochet": null,
  "trace_digest": "<sha256 hex>"
}
```

When ricochet occurs, `penetrated` is `false` and `ricochet` is an object with angles and `velocity_out`. `exit_energy_j` is energy remaining at stop.

### trace_digest

Lowercase hex SHA-256 of the UTF-8 string **`{replay_seq}|{ids}`** where `replay_seq` comes from the staged snapshot (`/app/docs/replay-epoch.md`) and `ids` are `trace_ids` from `/app/state/shot-snapshot.json` joined with commas **in traversal order** (no sorting). Example: replay `0` with ids `[103, 101, 102]` → hash input `"0|103,101,102"`. Export must read persisted snapshot fields for ledger, energy, and replay sequence; see `/app/docs/staging-snapshot.md` and `/app/docs/export-shot-contract.md`.

## simulate-batch

See `/app/docs/batch-contract.md`. Top-level fields: `batch`, `ticks`.
