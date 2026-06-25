#!/bin/bash
set -euo pipefail
IN="/app/output/h7_trace.json"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --in) IN="$2"; shift 2 ;;
    *) echo "usage: seal_trace.sh [--in path]" >&2; exit 2 ;;
  esac
done
exec /app/bin/h7stamp --in "${IN}" --patch
