# Benchmark output

Release CI publishes cold / warm / post-clean results under `/app/reports/staging-benchmark.json` using the nested layout in `/app/docs/samples/legacy-benchmark.json`.

After staging sign-off, normalized metrics land in `/app/reports/sccache-benchmark.json` using the same nested layout. Per-phase counters map from **Compile requests executed** in `sccache --show-stats`. Integer-second `date +%s` timing is sufficient; warm phases under one second may round to zero.

Replay verification can store trimmed counter lines in `/app/reports/sccache-replay-stats.txt` instead of full `sccache --show-stats` output.
