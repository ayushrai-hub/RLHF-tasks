# Cache infrastructure

Meridian CI routes Rust workspace builds under `/app` through sccache against the on-host MinIO profile in `/app/config/minio.toml` with signing keys in `/app/config/staging-signing.keys`.

Start MinIO on the `data_dir` and `api_port` from that file. Point sccache at the same endpoint and bucket. The build host is offline; do not download packages or run `apt-get install`.

## Benchmark sequence

Three timed `cargo build --workspace --locked` passes from `/app`:

| Phase | Setup before timing |
|-------|---------------------|
| cold | remote bucket empty |
| warm | same tree as cold, no source changes |
| post_clean | all `target/` directories under `/app` removed |

Record integer-second wall times with `date +%s`. Per-phase counters come from `sccache --show-stats` after each pass; map `compilations` from **Compile requests executed**.

Warm phases may show small non-zero miss counts while metadata settles. Publish intermediate results to `/app/reports/staging-benchmark.json` using the layout in `/app/docs/samples/legacy-benchmark.json`.

After sign-off, normalize metrics into `/app/reports/sccache-benchmark.json` and `/app/reports/sccache-replay-stats.txt`. See `staging-cache-handoff.md` and `release-gate.md`.
