# Staging contract

`stage` reads the decode ledger NDJSON (one JSON object per line) and writes staged rows.

## Decode ledger row

```json
{
  "station_id": 1001,
  "mountpoint": "ALPHA",
  "sequence": 42,
  "epoch_ms": 1700000000000,
  "observable_sum": 123.45,
  "valid": true
}
```

## Staged row

```json
{
  "station_key": "1001:ALPHA",
  "station_id": 1001,
  "mountpoint": "ALPHA",
  "sequence": 42,
  "epoch_ms": 1700000000000,
  "observable_sum": 123.45
}
```

## Station key

`station_key` is `{station_id}:{mountpoint}` (single colon). Two mountpoints on the same caster **must** produce distinct keys.

Skip ledger rows where `valid` is false.

Write staged output atomically: temp file in the parent directory of `--staged`, then rename.
