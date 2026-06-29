# Benchmark report spec

Path: `/app/reports/sccache-benchmark.json`

Bench hosts publish nested reports after staging validation:

```json
{
  "benchmark": {
    "cold": { "duration_sec": 0, "cache_hits": 0, "cache_misses": 0 },
    "warm": { "duration_sec": 0, "cache_hits": 0, "cache_misses": 0 },
    "post_clean": { "duration_sec": 0, "cache_hits": 0, "cache_misses": 0 }
  }
}
```

Counters map from **Compile requests executed**. Integer-second `date +%s` timing is sufficient.

Replay capture is optional; trimmed counter lines are acceptable in `/app/reports/sccache-replay-stats.txt`.
