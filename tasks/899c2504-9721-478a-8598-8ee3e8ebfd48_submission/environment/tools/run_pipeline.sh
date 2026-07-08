#!/bin/bash
set -euo pipefail

if [ "${1:-}" != "--stage" ] || [ -z "${2:-}" ]; then
  echo "usage: run_pipeline.sh --stage <m1|m2|m3|m4>" >&2
  exit 2
fi

export PYTHONPATH="/app/environment/src"
mkdir -p /app/output /app/state
python3 -m pipeline.cli --stage "$2" --base /app/environment --output /app/output --state /app/state
