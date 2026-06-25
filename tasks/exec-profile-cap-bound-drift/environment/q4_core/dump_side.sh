#!/bin/bash
set -euo pipefail
OUT="${1:-/app/work/cap_dump.txt}"
mkdir -p /app/work
if [[ -f /app/work/cap_store.tsv ]]; then
  cp /app/work/cap_store.tsv "$OUT"
else
  echo "empty" > "$OUT"
fi
