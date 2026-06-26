#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILES="${SCRIPT_DIR}/files"
DEST="/app/src/main/java/com/coastal/buoy/spectra"

cp "${FILES}/ProfileLoader.java" "${DEST}/config/ProfileLoader.java"
cp "${FILES}/SeriesReader.java" "${DEST}/io/SeriesReader.java"
cp "${FILES}/DriftCorrector.java" "${DEST}/process/DriftCorrector.java"
cp "${FILES}/GapInterpolator.java" "${DEST}/process/GapInterpolator.java"
cp "${FILES}/WaveletEngine.java" "${DEST}/process/WaveletEngine.java"
cp "${FILES}/Pipeline.java" "${DEST}/pipeline/Pipeline.java"

cd /app
mvn -q clean -DskipTests package
test -f /app/target/buoy-spectra-jar-with-dependencies.jar

mkdir -p /app/output
/app/scripts/run-spectra-pipeline.sh \
  --manifest /app/fixtures/manifests/storm-alpha.json \
  --output /app/output/storm-alpha-report.json
