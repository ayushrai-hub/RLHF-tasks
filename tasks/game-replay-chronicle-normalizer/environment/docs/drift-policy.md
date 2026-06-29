# Tick drift policy

Each shard header carries `drift_ms` (signed int32). For every event in that shard:

```
corrected_tick = raw_tick - drift_ms
```

Use 64-bit intermediate arithmetic; emit `tick` as uint32 in the chronicle (values are guaranteed to fit in tests).

Drift is per-shard and applied **before** global sort and deduplication.
