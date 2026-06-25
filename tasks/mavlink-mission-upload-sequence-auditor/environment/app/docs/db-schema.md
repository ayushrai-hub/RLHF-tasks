# SQLite schema

Default database path: `/app/data/missions.db`. `mission-ingest` creates the schema on first open.

**Preserve table and column names** — do not rename `waypoints` or `upload_commits`.

## upload_commits

| Column | Type | Notes |
|--------|------|-------|
| vehicle_id | TEXT | NOT NULL, part of PRIMARY KEY |
| upload_id | TEXT | NOT NULL, part of PRIMARY KEY |
| committed_at | INTEGER | default `strftime('%s','now')` |

Primary key: `(vehicle_id, upload_id)`.

A row indicates a successfully committed upload for that vehicle. Re-ingesting the same `(vehicle_id, upload_id)` must be a no-op (ignore the log body).

## waypoints

| Column | Type | Notes |
|--------|------|-------|
| vehicle_id | TEXT | NOT NULL |
| upload_id | TEXT | NOT NULL |
| seq | INTEGER | NOT NULL |
| lat_e7 | INTEGER | NOT NULL |
| lon_e7 | INTEGER | NOT NULL |
| alt_mm | INTEGER | NOT NULL |
| frame | INTEGER | NOT NULL |
| flags | INTEGER | NOT NULL |

Primary key: `(vehicle_id, upload_id, seq)` so the same `seq` in different uploads does not collide.

## Export clock (`exported_at_unix`)

When `mission-export` writes `/app/output/mission-upload-report.json` (or any `--out` path), compute:

`exported_at_unix = MISSION_EPOCH_BASE + max(seq)`

where `max(seq)` is taken **only** from `waypoints` rows matching the export's `vehicle_id` and `upload_id`. Default `MISSION_EPOCH_BASE` is `1704067200` when unset.

**Do not** use:

- `SELECT MAX(seq) FROM waypoints` without scoping to the export `(vehicle_id, upload_id)` pair (no vehicle-wide or global max).
- `ORDER BY rowid DESC LIMIT 1` (or “last inserted row”) to pick the epoch offset — physical ingest order can place a **lower** `seq` after a **higher** `seq` in the same upload. The export clock always uses the **maximum `seq` value** for that upload, not the last persisted row.

Cross-run: after multiple committed uploads share `/app/data/missions.db`, exporting upload `U` must ignore `seq` values from other `upload_id` values (even on the same `vehicle_id`) and from other vehicles. Rollup detail: `/app/docs/mission-rollup-rules.md` § Export clock.

## Failed ingest

Schema tables must exist after any ingest attempt, including failures. A failed upload leaves zero rows in `waypoints` and `upload_commits` for that `(vehicle_id, upload_id)` pair. Full ingest rules: `/app/docs/mission-ingest-rules.md`.
