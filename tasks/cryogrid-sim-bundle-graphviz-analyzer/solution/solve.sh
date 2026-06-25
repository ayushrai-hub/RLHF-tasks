#!/bin/bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILES="${SCRIPT_DIR}/files"

cp "${FILES}/bundle_spec_loader.cpp" "${APP_ROOT}/src/bundle_spec_loader.cpp"
cp "${FILES}/stage_graph.cpp" "${APP_ROOT}/src/stage_graph.cpp"
cp "${FILES}/variance_engine.cpp" "${APP_ROOT}/src/variance_engine.cpp"
cp "${FILES}/stability_check.cpp" "${APP_ROOT}/src/stability_check.cpp"
cp "${FILES}/dot_emitter.cpp" "${APP_ROOT}/src/dot_emitter.cpp"
cp "${FILES}/metrics_json.cpp" "${APP_ROOT}/src/metrics_json.cpp"

cd "${APP_ROOT}"
cmake --build /app/build -j"$(nproc)"
mkdir -p /app/output
