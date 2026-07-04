#!/bin/bash
set -euo pipefail

cmake -S /app -B /app/build >/dev/null
cmake --build /app/build >/dev/null
mkdir -p /app/bin
cp /app/build/flowgap /app/bin/flowgap
