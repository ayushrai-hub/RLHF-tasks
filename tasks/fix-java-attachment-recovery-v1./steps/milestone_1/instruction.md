Attachment recovery batch close is blocked. Nightly runs under /app are writing a bad report to /app/output/attachment-report.json.

The Java service reads attachment rows from /app/data/attachments.json, loads rates from /app/config/attachment-rules.properties (see /app/docs/config-keys.md), and writes to /app/output/attachment-report.json. Production logic lives in the multi-module Maven project under /app; the batch entry point is the attachment-batch module. Do not hardcode attachment totals or edit /app/data/attachments.json.

---

Production loaders must read `/app/config/attachment-rules.properties` directly per `/app/docs/config-keys.md`. Eligibility filtering follows approved-status and minimum attachment rules in `/app/docs/pricing-policy.md`, including case-insensitive approved status matching and the configured minimum attachment boundary. You are done with this step when the batch includes every eligible attachment row from `/app/data/attachments.json` without editing that file or the production config. From /app, run `mvn -q -B -o install -DskipTests` and then `mvn -q -B -o -pl attachment-batch exec:java` to regenerate /app/output/attachment-report.json and confirm eligibility.
