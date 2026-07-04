# Station audit ledger contract

Path: `/app/state/rtcmctl-station-ledger.json`

Published by `publish-ledger`:

```json
{
  "db_path": "/path/to/db",
  "event_count": 3,
  "chain_digest": "<sha256-hex>"
}
```

## chain_digest

Query `station_audit` ordered by `created_at ASC`, `event_id ASC`. Serialize the array of objects:

```json
[{"event_id":"...","station_key":"...","action":"...","created_at":"..."}]
```

Use compact JSON (`serde_json::to_string` with no spaces). SHA-256 hex digest of UTF-8 bytes.
