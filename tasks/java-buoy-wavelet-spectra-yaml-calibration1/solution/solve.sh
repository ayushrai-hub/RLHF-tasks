#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILES="${SCRIPT_DIR}/files"
DEST="/app/src/main/java/com/coastal/buoy/spectra"

cp "${FILES}/Main.java" "${DEST}/Main.java"
cp "${FILES}/config/ProfileHasher.java" "${DEST}/config/ProfileHasher.java"
cp "${FILES}/ProfileLoader.java" "${DEST}/config/ProfileLoader.java"
cp "${FILES}/SeriesReader.java" "${DEST}/io/SeriesReader.java"
cp "${FILES}/io/StagingReader.java" "${DEST}/io/StagingReader.java"
cp "${FILES}/io/StagingWriter.java" "${DEST}/io/StagingWriter.java"
cp "${FILES}/DriftCorrector.java" "${DEST}/process/DriftCorrector.java"
cp "${FILES}/GapInterpolator.java" "${DEST}/process/GapInterpolator.java"
cp "${FILES}/WaveletEngine.java" "${DEST}/process/WaveletEngine.java"
cp "${FILES}/pipeline/Pipeline.java" "${DEST}/pipeline/Pipeline.java"
cp "${FILES}/pipeline/IngestStage.java" "${DEST}/pipeline/IngestStage.java"
cp "${FILES}/pipeline/ExportStage.java" "${DEST}/pipeline/ExportStage.java"
cp "${FILES}/model/StagingSnapshot.java" "${DEST}/model/StagingSnapshot.java"
cp "${FILES}/model/CommitBind.java" "${DEST}/model/CommitBind.java"

cd /app
mvn -q clean -DskipTests package
test -f /app/target/buoy-spectra-jar-with-dependencies.jar

mkdir -p /app/output /app/state
/app/scripts/run-spectra-pipeline.sh \
  --manifest /app/fixtures/manifests/storm-alpha.json \
  --output /app/output/storm-alpha-report.json
