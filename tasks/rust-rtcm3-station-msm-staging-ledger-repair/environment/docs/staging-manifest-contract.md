# Staging manifest contract

Path: `/app/state/rtcmctl-staging-manifest.json`

Written atomically by `stage` immediately after the staged NDJSON file is renamed into place.

## Fields

```json
{
  "staged_path": "/absolute/path/to/staged.ndjson",
  "row_count": 3,
  "station_keys": ["1001:ALPHA", "1001:BETA", "2002:GAMMA"],
  "keys_digest": "<sha256 hex>"
}
```

## station_keys

Unique `station_key` values from valid staged rows, sorted **lexicographically ascending** (Unicode code-point order).

## keys_digest

SHA-256 hex digest of UTF-8 bytes formed by joining the **sorted** `station_keys` with a single newline (`\n`) between entries. No trailing newline after the last key.

Example for keys `["1001:ALPHA", "2001:BETA"]`:

```
1001:ALPHA\n2001:BETA
```

## persist gate

Before opening the SQLite batch transaction, `persist` must:

1. Load the manifest from `/app/state/rtcmctl-staging-manifest.json`
2. Reject when `manifest.staged_path` differs from the `--staged` argument
3. Reject when `manifest.row_count` differs from the number of non-empty staged lines
4. Recompute `keys_digest` from staged rows (sorted unique keys) and reject on mismatch

Missing manifest or any mismatch is a hard error — no partial SQLite writes.
