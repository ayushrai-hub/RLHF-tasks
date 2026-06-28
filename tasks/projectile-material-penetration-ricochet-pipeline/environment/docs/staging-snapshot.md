# Shot staging snapshot

Every `ballctl integrate-shot` run writes **`/app/state/shot-snapshot.json`** after trajectory integration and replay sequencing. Export is a separate `export-shot` step (see `/app/docs/export-shot-contract.md`).

Schema:

```json
{
  "staging_version": 1,
  "stack": "multi-layer",
  "seed": 42,
  "replay_seq": 0,
  "path_ledger_m": 0.012,
  "exit_energy_j": 2492.8,
  "penetrated": true,
  "layers": [ ... ],
  "ricochet": null,
  "trace_ids": [103, 102]
}
```

`replay_seq` is assigned per `/app/docs/replay-epoch.md`. `trace_ids` lists `physics_id` values in **traversal order** (one entry per layer touched, including partial ricochet stops). Staging must persist the integrated `path_ledger_m` and `exit_energy_j` exactly as computed — export reads the snapshot file and must not re-derive ledger totals from layer rows.

Export adds `trace_digest` per `/app/docs/export-schema.md`. Integration runs in `integrator`; replay sequencing in `replay_gate`; staging persists; `export_stage` publishes the final shot JSON.
