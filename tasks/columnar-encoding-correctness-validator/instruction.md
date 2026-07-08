The columnar encoding service under /app must validate twenty bundled segment fixtures and publish one integrity report for CI. Implement segment reconciliation in /app/codec/reconcile/reconcile.go and keep /app/validator/main.go plus /app/writer/emit.go as shipped. After each edit run make build from /app until /app/bin/columnar-validator exceeds 2048 bytes.

Write /app/output/encoding_integrity_report.json per /app/spec/REPORT_SPEC.md and /app/spec/SEGMENT_FORMAT.md. Decode plain, dictionary, RLE, bitpack, and delta encodings, verify page checksums, statistics, pruning counts, compaction order, parallel slot uniqueness, and metadata drift. Honor COLUMNAR_FIXTURE_DIR when set. Do not modify /app/fixtures, /app/spec, or /app/rules/encoding_policy.yaml.

Derive every report field from reconciliation logic, not embedded checksum tables. Follow the output schema and fault-code definitions in REPORT_SPEC.
