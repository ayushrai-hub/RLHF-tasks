# Staging cache handoff (archived)

Superseded by the current staging workflow documented in `/app/docs/staging-cache-handoff.md`.

When validating cache plumbing before promoting a workspace, engineers pointed sccache at the staging MinIO profile under `/app/config/` (`staging-minio.toml` and `staging-signing.keys`). The staging bucket listened on `http://127.0.0.1:9001` with data under `/var/minio/staging`.

They ran the same cold / warm / post-clean sequence and published under `/app/reports/staging-benchmark.json`.
