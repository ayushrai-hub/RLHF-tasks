#!/usr/bin/env bash
set -euo pipefail

MANIFEST=""
OUTPUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --manifest) MANIFEST="$2"; shift 2 ;;
    --output) OUTPUT="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [[ -z "${MANIFEST}" || -z "${OUTPUT}" ]]; then
  echo "usage: run-spectra-pipeline.sh --manifest <abs.json> --output <abs-report.json>" >&2
  exit 2
fi

JAR="/app/target/buoy-spectra-jar-with-dependencies.jar"
if [[ ! -f "${JAR}" ]]; then
  echo "missing jar: ${JAR}" >&2
  exit 1
fi

java -jar "${JAR}" process --manifest "${MANIFEST}" --output "${OUTPUT}"
