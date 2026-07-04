# Preservation report schema

Path: /app/output/preservation-report.json

Fields:
- schema_version: 1
- artifact_count (integer) — number of validated artifacts in collection-snapshot.json
- migration_count (integer) — length of migration_pairs in preservation-atlas.json
- wave_count (integer) — length of preservation_waves in preservation-atlas.json
- report_fingerprint (string) — lowercase hex SHA-256 of compact preservation atlas JSON

report_fingerprint is the lowercase hex SHA-256 of json.dumps(atlas, separators=(",", ":"), sort_keys=True) where atlas is the preservation-atlas object before pretty-printing.
