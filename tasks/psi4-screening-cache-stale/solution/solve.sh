#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -f "${SCRIPT_DIR}/oracle.patch" ]]; then
  echo "oracle.patch missing" >&2
  exit 1
fi

cd "${SCRIPT_DIR}"
patch -d /app -p1 --batch < oracle.patch

cd /app/environment
cmake --build build --parallel

rm -rf /app/runtime /app/output/p7_trace.json
mkdir -p /app/runtime /app/output
/app/environment/tools/p7_run --cold
/app/environment/tools/p7_emit --out /app/output/p7_trace.json

if [[ ! -s /app/output/p7_trace.json ]]; then
  echo "p7_trace.json empty after oracle replay" >&2
  exit 1
fi
