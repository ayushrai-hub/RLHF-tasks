#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build bin
cmake -S . -B build
cmake --build build -j"$(nproc)"
cp build/beam-envelope bin/beam-envelope
