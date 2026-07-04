# Mutation seal contract

Path: `/app/state/rtcmctl-mutation-seal.json`

```json
{
  "db_path": "/path/to/db",
  "ledger_chain_digest": "<from station ledger>",
  "event_count": 3,
  "db_fingerprint": "<sha256 of database file bytes>",
  "tail_created_at": "<last audit created_at>"
}
```

`db_fingerprint` is SHA-256 hex of the raw SQLite file bytes (not the path string).

`tail_created_at` is the `created_at` of the last row in `station_audit` when sorted by `(created_at ASC, event_id ASC)`, or empty string when no rows.

`seal-mutations` must verify the on-disk station ledger `chain_digest` matches live SQLite before writing the seal.
