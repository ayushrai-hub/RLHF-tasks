#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FILES="${SCRIPT_DIR}/files"

cp "${FILES}/keyword_lexer.cpp" "${APP_ROOT}/src/keyword_lexer.cpp"
cp "${FILES}/wcs_matrix.cpp" "${APP_ROOT}/src/wcs_matrix.cpp"
cp "${FILES}/projection.cpp" "${APP_ROOT}/src/projection.cpp"
cp "${FILES}/pixel_map.cpp" "${APP_ROOT}/src/pixel_map.cpp"
cp "${FILES}/atlas_writer.cpp" "${APP_ROOT}/src/atlas_writer.cpp"

bash "${APP_ROOT}/scripts/build.sh"
test -x /app/bin/wcs-atlas
