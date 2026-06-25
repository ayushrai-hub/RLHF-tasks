#!/bin/bash
set -euo pipefail
PHASE="${1:-}"
OUT_DIR="/app/output"
JAR="/app/build/libs/trace-audit-cli.jar"
mkdir -p "$OUT_DIR"
if [[ ! -f "$JAR" ]]; then
  echo "missing jar; run build_all.sh first" >&2
  exit 1
fi
case "$PHASE" in
  index)
    java -jar "$JAR" index "$OUT_DIR/trace_index.json"
    ;;
  audit)
    java -jar "$JAR" index "$OUT_DIR/trace_index.json"
    java -jar "$JAR" audit "$OUT_DIR/trace_index.json" "$OUT_DIR/policy_audit.json"
    ;;
  clean)
    java -jar "$JAR" index "$OUT_DIR/trace_index.json"
    java -jar "$JAR" audit "$OUT_DIR/trace_index.json" "$OUT_DIR/policy_audit.json"
    java -jar "$JAR" clean "$OUT_DIR/policy_audit.json" "$OUT_DIR/cleanup_report.json"
    ;;
  verify)
    java -jar "$JAR" index "$OUT_DIR/trace_index.json"
    java -jar "$JAR" audit "$OUT_DIR/trace_index.json" "$OUT_DIR/policy_audit.json"
    java -jar "$JAR" verify "$OUT_DIR/verification_report.json"
    ;;
  *)
    echo "usage: milestone_probes.sh index|audit|clean|verify" >&2
    exit 2
    ;;
esac
