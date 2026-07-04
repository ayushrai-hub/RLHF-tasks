Fix report generation in the attachment-report module. `netAttachment` must follow the documented formula in `/app/docs/pricing-policy.md`. Sort attachments by `netAttachment` descending, then `id` ascending. The report must include `generatedAt`, all required row and summary fields, Gson pretty-printing with a space after each colon, and two-decimal JSON money literals.

Regenerate `/app/output/attachment-report.json` from /app with `mvn -q -B -o install -DskipTests` followed by `mvn -q -B -o -pl attachment-batch exec:java`. Do not hardcode totals or write the report with a script.
