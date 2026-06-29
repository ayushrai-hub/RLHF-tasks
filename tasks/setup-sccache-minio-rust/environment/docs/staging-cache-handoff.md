# Staging cache handoff

Validate remote compile caching on a fresh host with `/app/config/minio.toml` and `/app/config/staging-signing.keys`.

Run the cold / warm / post-clean sequence against that endpoint and publish under `/app/reports/staging-benchmark.json`. Production hosts read this handoff when the file is present.

Warm phases may record small non-zero miss counts while metadata warms. Integer-second timing is sufficient.

After sign-off, operators copy object keys into the production bucket from `backend-cache.toml` and normalize release metrics into `/app/reports/sccache-benchmark.json`.
