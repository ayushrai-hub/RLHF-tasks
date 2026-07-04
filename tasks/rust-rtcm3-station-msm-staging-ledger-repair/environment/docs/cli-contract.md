# CLI contract

Binary: `/app/bin/rtcmctl`

| Command | Flags | Behavior |
|---------|-------|----------|
| `init` | `--db PATH` | Apply `schema.sql` |
| `decode` | `--capture PATH`, `--ledger PATH` | Parse RTCM3 capture (`rtcm3-framing.md`), write decode ledger NDJSON |
| `stage` | `--ledger PATH`, `--staged PATH` | Read decode ledger, write staged rows (`staging-contract.md`) |
| `persist` | `--db PATH`, `--staged PATH`, `--ingest-at RFC3339` | Upsert stations from staged rows only |
| `ingest` | `--db PATH`, `--capture PATH`, `--ingest-at RFC3339` | `decode`, `stage`, `persist`, `publish-ledger`, `seal-mutations`, `refresh-snapshot` |
| `publish-ledger` | `--db PATH` | Publish station audit ledger (`station-ledger-contract.md`) |
| `seal-mutations` | `--db PATH` | Publish mutation seal (`mutation-seal-contract.md`) |
| `refresh-snapshot` | `--db PATH`, `--as-of RFC3339` | Materialize ingest counters and publish snapshot (`snapshot-contract.md`) |
| `export` | `--db PATH`, `--as-of RFC3339`, `json` | Validate snapshot and emit health report JSON |

Exit non-zero on validation errors. Rebuild with `/app/scripts/verifier-rebuild.sh`.

Default paths:

- decode ledger: `/app/state/rtcmctl-decode-ledger.ndjson`
- staged rows: `/app/state/rtcmctl-staging/staged.ndjson`
- snapshot: `/app/state/rtcmctl-snapshot.json`
