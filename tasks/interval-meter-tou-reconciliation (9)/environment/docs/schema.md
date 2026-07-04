# Report schema

`/app/output/reconciliation_report.json`

- `timezone`: string
- `all_reconciled`: boolean
- `fixture_sets`: array of objects with `name` and `meters`
- `meters`: object keyed by meter id with numeric tier totals, demand peak, rollover and gap counters, reconciliation flags

Tier keys: `off_peak`, `mid_peak`, `on_peak`.
