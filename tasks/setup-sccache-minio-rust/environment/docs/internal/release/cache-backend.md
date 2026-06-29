# Cache backend

Release verification on this build host uses `/app/config/backend-cache.toml` with signing keys in `/app/config/backend-signing.keys`. Default bench-host templates under `/app/config/` describe staging only.

Start MinIO using the production `data_dir` and `api_port` from `backend-cache.toml`. Wire sccache to the same endpoint, bucket, region, and keys. Compile artifacts must land in that bucket under the configured object storage root.

Workspace builds under `/app` route through sccache against that backend. The environment is offline; do not download packages or run `apt-get install`.

## Benchmark sequence

Three timed `cargo build --workspace --locked` passes from `/app`:

| Phase | Setup before timing |
|-------|---------------------|
| cold | remote bucket empty |
| warm | same tree as cold, no source changes |
| post_clean | all `target/` directories under `/app` removed |

Each pass records fractional-second wall-clock duration and per-phase cache counters only. Reset sccache statistics before each timed phase so counters are not cumulative across phases.

The warm phase must record zero misses and zero compilations in its phase counters.

`/app/target/debug/meridian-cli` must exist when setup completes.
