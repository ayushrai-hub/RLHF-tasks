# Mission upload auditor

Ground-station capture hardware writes `.mseq` binary upload logs. The auditor ingests those logs into SQLite and exports JSON summaries for flight review.

## Components

- `mission-ingest` — parse logs, validate CRC, commit waypoints per upload session
- `mission-export` — read committed waypoints and emit JSON summaries

## Normative contracts

| Document | Contents |
|----------|----------|
| `/app/docs/mseq-format.md` | Wire layout, X.25 CRC scope, flag bits |
| `/app/docs/mission-ingest-rules.md` | Ingest validation, transactions, idempotency |
| `/app/docs/mission-rollup-rules.md` | Altitude, distance rollup, hold/suppress, export clock |
| `/app/docs/db-schema.md` | `waypoints` and `upload_commits` tables |
| `/app/docs/export-schema.md` | Export JSON field types and ordering |
| `/app/docs/cli.md` | Build, ingest, export, environment variables |

Vehicle home altitudes for relative-frame conversion: `/app/config/vehicle-profile.json`.
