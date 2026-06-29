# Deployment notes

Fresh bench hosts wire sccache from `/app/config/minio.toml` and `/app/config/staging-signing.keys`. The alternate `cache-endpoint.toml` profile mirrors the same staging endpoint for legacy automation.

Production release verification on promoted hosts uses `/app/config/backend-cache.toml` with `/app/config/backend-signing.keys` after object promotion from staging.

Do not edit crate sources under `/app/crates` during benchmark runs.
