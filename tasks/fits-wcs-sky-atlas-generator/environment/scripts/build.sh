#!/usr/bin/env bash
set -euo pipefail
cd /app
rm -rf /app/build
GEN="${CMAKE_GENERATOR:-Ninja}"
cmake -S /app -B /app/build -G "${GEN}"
cmake --build /app/build
cp /app/build/wcs-atlas /app/bin/wcs-atlas
