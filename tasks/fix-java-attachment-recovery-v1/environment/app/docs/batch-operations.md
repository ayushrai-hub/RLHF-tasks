# Batch Operations

Production nightly batch reads `/app/data/attachments.json`, loads
`/app/config/attachment-rules.properties`, and writes `/app/output/attachment-report.json`.

Staging override files and legacy loaders under `attachment-engine/legacy/` are not
used by the production batch entrypoint (`com.attachment.batch.Main`).
