# Cache infrastructure (staging — archived)

Meridian CI previously validated remote compile caching against the staging MinIO profile before promoting workspaces. Backend settings were under `/app/config/` (`staging-minio.toml` and `staging-signing.keys`).

Workspace builds under `/app` routed through sccache against `http://127.0.0.1:9001`. Integer-second `date +%s` timing was sufficient.

Results were published to `/app/reports/staging-benchmark.json` using the nested layout in `/app/docs/samples/legacy-benchmark.json`. Counters mapped from **Compile requests executed** in `sccache --show-stats`.

Do not use this profile for production CI on current build hosts.
