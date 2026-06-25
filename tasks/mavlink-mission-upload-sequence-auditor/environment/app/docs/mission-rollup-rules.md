# Mission rollup rules

Normative behavior for altitude conversion, distance totals, and flag semantics on export. JSON field names and types are in `/app/docs/export-schema.md`.

## Altitude

Home altitudes come from `/app/config/vehicle-profile.json` (`home_alt_m` per `vehicle_id`).

| Frame | Id | `alt_meters` |
|-------|-----|--------------|
| GLOBAL | `0` | `round3(alt_mm / 1000.0)` |
| GLOBAL_RELATIVE_ALT | `3` | `round3((alt_mm / 1000.0) - home_alt_m)` |
| GLOBAL_TERRAIN_ALT | `10` | `round3(alt_mm / 1000.0)` |

Only frame `3` subtracts home; frames `0` and `10` use absolute MSL meters.

`round3(x)` means half-away-from-zero rounding to three decimal places (same as `(x * 1000).round() / 1000`).

## Distance rollup

`total_distance_m` sums haversine great-circle distance in meters between consecutive waypoints ordered by **ascending `seq`**, not physical file order. Earth radius: `6_371_000` meters.

- One waypoint → `0.0`.
- Round the **total** with `round3` after summing raw leg distances — do not round each leg before summing.

Compute distances from **all persisted rows for the upload ordered by `seq`**, not from the export-filtered `waypoints` array.

### Hold (`flags & 0x02`)

When the **destination** waypoint of a consecutive pair has `flags & 0x02` in SQLite, omit that leg from the sum. A hold bit on the source waypoint does not skip the outbound leg. Hold does not remove the waypoint from export or change altitude fields.

### Suppress (`flags & 0x04`)

Rows with `flags & 0x04` are omitted from export `waypoints[]` but remain in SQLite and participate in distance rollup (subject to hold). When both `0x04` and `0x02` are set, apply both: omit from export and treat as a hold destination for the inbound leg.

When **every** persisted row for an upload has `flags & 0x04`, export `waypoints` is `[]` but `total_distance_m` still sums legs between those suppressed rows (after hold rules). `upload_qc_pass` is `true` when `total_distance_m <= max_route_m` and there are no exported frame-`3` rows to check against `max_rel_alt_m`.

## Empty upload

When a committed upload has zero waypoint rows: `waypoints` is `[]`, `total_distance_m` is `0.0`, and `exported_at_unix` is `MISSION_EPOCH_BASE + 0` even when other uploads exist in the database.

## Export clock

`exported_at_unix = MISSION_EPOCH_BASE + max(seq)` over waypoints for this export's `vehicle_id` and `upload_id` only. Default `MISSION_EPOCH_BASE` is `1704067200` when unset. Ignore rows from other uploads or vehicles.

Use the **maximum `seq` value** for that upload — not `ORDER BY rowid DESC` / last-inserted row when file byte order disagrees with ascending `seq` (see `/app/docs/db-schema.md` § Export clock).

## Upload QC gate

`upload_qc_pass` is computed from the export `vehicle_id`, the export `waypoints` array (after suppress filtering), and `total_distance_m`. Limits come from `/app/config/vehicle-profile.json` — see `/app/docs/vehicle-profile.md`.

- `total_distance_m` must be less than or equal to `max_route_m`.
- For each exported waypoint with `frame == 3`, `alt_meters` must satisfy `-max_rel_alt_m <= alt_meters <= max_rel_alt_m`.
- Frames `0` and `10` are not compared to `max_rel_alt_m`.

Export still writes the JSON document when QC fails; set `upload_qc_pass` to `false` when any limit is exceeded.

## audit_hash

After computing `waypoints`, `total_distance_m`, and rounding per the rules above, build the hash input object documented in `/app/docs/export-schema.md` (`vehicle_id`, `upload_id`, `waypoints`, `total_distance_m` only). Serialize with `serde_json::to_string` (`f64` and integer field rules in export-schema). SHA-256 the compact JSON UTF-8 bytes; write lowercase hex to `audit_hash`.
