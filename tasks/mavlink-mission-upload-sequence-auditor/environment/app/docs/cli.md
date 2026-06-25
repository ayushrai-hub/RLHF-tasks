# CLI reference

`mission-ingest` and `mission-export` are **compiled Rust binaries** installed to `/app/bin/` (not editable text). Source lives under `/app/src/`; change behavior there, then rebuild.

## Build

Default images ship prebuilt binaries in `/app/bin/`. After editing Rust sources, recompile with:

```bash
/app/scripts/oracle-build.sh
```

`oracle-build.sh` runs `cargo build --release --locked` and installs `mission-ingest` and `mission-export` into `/app/bin/`.

`/app/scripts/build.sh` only checks that `/app/bin/mission-ingest` and `/app/bin/mission-export` exist (used by the verifier).

## mission-ingest

```
mission-ingest --db <sqlite-path> --log <mseq-file> --upload-id <id> --vehicle <vehicle-id>
```

Opens or creates the database schema, parses the `.mseq` log per `/app/docs/mseq-format.md` and `/app/docs/mission-ingest-rules.md`, and commits waypoints when validation succeeds.

Exit code `0` on success or idempotent replay of an already committed `(vehicle_id, upload_id)` pair. On replay, stored waypoint rows for that pair must remain unchanged from the first successful commit. Non-zero on validation or CRC failure.

## mission-export

```
mission-export --db <sqlite-path> --vehicle <vehicle-id> --upload-id <id> --out <json-path> [--profile /app/config/vehicle-profile.json]
```

Reads committed waypoints for the vehicle/upload pair and writes JSON per `/app/docs/export-schema.md` and `/app/docs/mission-rollup-rules.md`.

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| MISSION_EPOCH_BASE | `1704067200` | Export clock base (see `/app/docs/mission-rollup-rules.md`) |
