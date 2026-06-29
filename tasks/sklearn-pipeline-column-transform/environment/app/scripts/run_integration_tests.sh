
#!/usr/bin/env bash
set -euo pipefail
OUT=/tmp/skct_integration
rm -rf "$OUT" && mkdir -p "$OUT"
J="java -Djava.library.path=/app/native -jar /app/java/build/libs/skct-pipeline-1.0.0.jar"
CORPUS=/app/feature_corpus/sklearn_pipeline_column_transform_corpus.md
BUNDLE=/app/fixtures/bundles/pipeline_alpha_v3.json
BETA=/app/fixtures/bundles/pipeline_beta_v1.json

$J feature-ingest --bundle "$BUNDLE" --corpus "$CORPUS" --out "$OUT/ingest"
$J column-transform-train --bundle "$BUNDLE" --corpus "$CORPUS" --out "$OUT/train"
$J pipeline-export --bundle "$BUNDLE" --corpus "$CORPUS" --out "$OUT/export"
mkdir -p "$OUT/audit"
cp "$OUT/export/portable_pipeline.json" "$OUT/audit/"
$J parity-audit --bundle "$BUNDLE" --corpus "$CORPUS" --out "$OUT/audit"
test -f "$OUT/ingest/feature_manifest.json"
test -f "$OUT/train/transform_report.json"
test -f "$OUT/export/pipeline_registry.json"
test -f "$OUT/export/portable_pipeline.json"
test -f "$OUT/audit/parity_audit.json"

$J feature-ingest --bundle "$BETA" --corpus "$CORPUS" --out "$OUT/beta_ingest"
$J column-transform-train --bundle "$BETA" --corpus "$CORPUS" --out "$OUT/beta_train"
$J pipeline-export --bundle "$BETA" --corpus "$CORPUS" --out "$OUT/beta_export"
mkdir -p "$OUT/beta_audit"
cp "$OUT/beta_export/portable_pipeline.json" "$OUT/beta_audit/"
$J parity-audit --bundle "$BETA" --corpus "$CORPUS" --out "$OUT/beta_audit"
test -f "$OUT/beta_ingest/feature_manifest.json"
test -f "$OUT/beta_train/transform_report.json"
test -f "$OUT/beta_export/pipeline_registry.json"
test -f "$OUT/beta_export/portable_pipeline.json"
test -f "$OUT/beta_audit/parity_audit.json"
