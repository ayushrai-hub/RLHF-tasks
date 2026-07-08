#!/usr/bin/env bash
set -euo pipefail
WORKSPACE="${1:-/app/data/workspace}"
bash /app/environment/scripts/setup_fanout.sh "${WORKSPACE}" /app/environment/fixtures/wave
