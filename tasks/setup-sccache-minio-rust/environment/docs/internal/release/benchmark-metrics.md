# Benchmark metrics

Release benchmark JSON at `/app/reports/sccache-benchmark.json` uses flat top-level keys: `cold_seconds`, `warm_seconds`, `post_clean_seconds`, `cold`, `warm`, `post_clean`. Phase blocks are top-level objects — not nested under `phases`, `benchmark`, or legacy names like `cache_hits` or `duration_sec`.

Each phase object contains integer `hits`, `misses`, and `compilations` from that phase's cache statistics output. Counter mapping is in `stat-mapping.md`; timing thresholds are in `timing-bounds.md`.

## Replay verification (required)

After the benchmark report is written, run one additional post-clean verification build in the same shell session (delete every `target/` directory under `/app` first) and save the full raw `sccache --show-stats` output to `/app/reports/sccache-replay-stats.txt`. Trimmed counter excerpts are not acceptable.
