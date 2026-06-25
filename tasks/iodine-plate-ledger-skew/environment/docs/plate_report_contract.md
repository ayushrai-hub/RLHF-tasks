# Plate Report Contract

## Driver

- Entry: `/app/target/release/iodine-plate plate`
- Flags: `--ledger <scenario>`, `--output /app/output/iodine_plate_report.json`
- Bundled scenario ids: `tab_x`, `tab_v`, `tab_t`, `tab_y`, `tab_z`, `tab_w`, `tab_s`, `tab_trim`, `tab_lm`

## Paths

- Scenario manifests: `/app/fixtures/scenarios/<scenario>.json`
- Segment bytes: `/app/fixtures/segments/<scenario>/`
- Profile tables: `/app/profiles/<profile>.toml`
- Head stamps: `/app/var/cache/head/<scenario>.txt`
- Generation markers: `/app/var/cache/gen/<scenario>.txt`
- Trace sidecar: `/app/output/iodine_plate_trace.tsv`
- Cache salt: `/app/policy/cache_salt.txt`

## Report schema

The JSON report at `/app/output/iodine_plate_report.json` carries:

- `scenario` — scenario label
- `head_seq` — `u32`
- `records_applied` — `u32`
- `digest_chain` — string
- `segments` — array of objects with `name`, `seq`, and `digest_match`

PLT5 byte layout, plate lane field, digest anchors, and digest span: see `/app/docs/plt5_plate_format.md`.

## Trim profiles

Scenario manifests may include optional trim fields `rollback_after` and `prune_below`, plus an optional `profile` string naming a TOML file under `/app/profiles/`.

Profile TOML format:

```toml
trim_sequence = ["rollback_after", "prune_below"]
lane_mask = 65535
modulo_prune = 3
```

`lane_mask` defaults to 65535 (all lanes). When not 65535, keep only rows whose plate lane bit is set in the mask. `modulo_prune` may also appear in the scenario manifest JSON; both sources apply when present.

`digest_chain` values are the literal strings `empty`, `valid`, or `broken`.

## Trace sidecar

`/app/output/iodine_plate_trace.tsv` column names:

- Header line: `seq,plate_lane,digest_match,retained`
- Field delimiter: ASCII comma (`,`) on every line, including the header

## Cache

Cache artifact paths:

- `/app/var/cache/head/<scenario>.txt` — stores `head_seq`
- `/app/var/cache/gen/<scenario>.txt` — stores generation stamp
- Salt source: `/app/policy/cache_salt.txt`
