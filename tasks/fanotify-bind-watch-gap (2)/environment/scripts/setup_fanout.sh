#!/usr/bin/env bash
set -euo pipefail

WORKSPACE="${1:-/app/data/workspace}"
FIXTURES="${2:-/app/environment/fixtures/wave}"

mkdir -p "${WORKSPACE}/published" \
         "${WORKSPACE}/layers/host" \
         "${WORKSPACE}/layers/work" \
         "${WORKSPACE}/archive/gen1" \
         "${WORKSPACE}/archive/gen2"

echo "1" > "${WORKSPACE}/layers/host/wave_gen"
echo "1" > "${WORKSPACE}/layers/work/wave_gen"

if [[ -f "${FIXTURES}/gen1/active.log" ]]; then
  cp "${FIXTURES}/gen1/active.log" "${WORKSPACE}/published/active.log"
  cp "${FIXTURES}/gen1/active.log" "${WORKSPACE}/layers/host/active.log"
  cp "${FIXTURES}/gen1/active.log" "${WORKSPACE}/layers/work/active.log"
fi
