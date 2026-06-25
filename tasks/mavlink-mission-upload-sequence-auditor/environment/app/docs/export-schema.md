# Mission export JSON schema

`mission-export` writes a UTF-8 JSON document to the path given by `--out`.

Computed altitude, distance, flag handling, export clock, QC gate, and hash rules are in `/app/docs/mission-rollup-rules.md`. Vehicle limits are in `/app/docs/vehicle-profile.md`.

## Top-level object

| Field | Type | Rule |
|-------|------|------|
| vehicle_id | string | matches `--vehicle` |
| upload_id | string | matches `--upload-id` |
| waypoints | array | see waypoint object; sorted ascending by `seq`; flag filtering per rollup rules |
| total_distance_m | number | three decimal places; see rollup rules |
| exported_at_unix | integer | see rollup rules |
| upload_qc_pass | boolean | see rollup rules and vehicle profile limits |
| audit_hash | string | lowercase hex SHA-256; see rollup rules |

## Waypoint object

| Field | Type | Rule |
|-------|------|------|
| seq | integer | sequence index from ingest |
| lat_deg | number | `lat_e7 / 1e7` |
| lon_deg | number | `lon_e7 / 1e7` |
| alt_meters | number | three decimal places; see rollup rules |
| frame | integer | MAVLink frame id from ingest |

Field order in the written JSON follows the export struct declaration order above.

## audit_hash input

Serialize a JSON object with **only** these keys in this order: `vehicle_id`, `upload_id`, `waypoints`, `total_distance_m`. Use compact JSON with **no insignificant whitespace** — the same bytes as Rust `serde_json::to_string` on the hash payload struct.

### JSON number encoding (normative)

| Field | JSON type | Encoding rule |
|-------|-----------|---------------|
| `vehicle_id`, `upload_id` | string | JSON string with standard escaping (`serde_json`) |
| `waypoints[].seq` | integer | JSON integer (no fractional part); matches ingest `u16` |
| `waypoints[].frame` | integer | JSON integer (no fractional part); matches ingest `u8` |
| `waypoints[].lat_deg`, `waypoints[].lon_deg`, `waypoints[].alt_meters` | number | `f64` serialized exactly as `serde_json::to_string` on each field |
| `total_distance_m` | number | `f64` after `round3`; same `serde_json` `f64` encoding |

Do **not** use Python `json.dumps` default float formatting for hash input — it is not guaranteed to match `serde_json`. Each `f64` in the hash payload must use the same decimal form as Rust `serde_json` (shortest decimal for the IEEE-754 value).

Waypoint objects inside the hash array use field order: `seq`, `lat_deg`, `lon_deg`, `alt_meters`, `frame` (struct declaration order). Omit suppressed rows (`flags & 0x04`) from the hash `waypoints` array, matching export `waypoints[]`.

Hash the UTF-8 bytes with SHA-256 and encode as lowercase hex. Do **not** include `exported_at_unix`, `upload_qc_pass`, or `audit_hash` in the hash input.

### Worked example (empty upload)

For `vehicle_id` = `"V1"`, `upload_id` = `"empty-00"`, no waypoint rows after commit:

Compact payload bytes (exact):

```text
{"vehicle_id":"V1","upload_id":"empty-00","waypoints":[],"total_distance_m":0.0}
```

`audit_hash` = `sha256` of those bytes as lowercase hex (see `/app/docs/mission-rollup-rules.md` empty-upload rules for `total_distance_m` and `exported_at_unix`).
