# Release gate

## Benchmark report

Path: `/app/reports/sccache-benchmark.json`

Production CI ingests staging benchmark runs after handoff approval. Reports use the nested layout from `/app/docs/samples/legacy-benchmark.json`:

```json
{
  "benchmark": {
    "cold": { "duration_sec": 0, "cache_hits": 0, "cache_misses": 0 },
    "warm": { "duration_sec": 0, "cache_hits": 0, "cache_misses": 0 },
    "post_clean": { "duration_sec": 0, "cache_hits": 0, "cache_misses": 0 }
  }
}
```

Each phase object maps counters from **Compile requests executed** in `sccache --show-stats`. Integer-second `date +%s` timing is sufficient; warm phases under one second may round to zero.

## Replay verification

Optional. When present, store trimmed counter lines in `/app/reports/sccache-replay-stats.txt` rather than full `sccache --show-stats` output.
