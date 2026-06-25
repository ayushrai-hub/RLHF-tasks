#!/usr/bin/env bash
set -euo pipefail
for bin in mission-ingest mission-export; do
  if [[ ! -x "/app/bin/${bin}" ]]; then
    echo "missing /app/bin/${bin}" >&2
    exit 1
  fi
done
