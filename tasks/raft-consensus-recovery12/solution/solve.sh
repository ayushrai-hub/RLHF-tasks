#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="${APP_ROOT:-/app}"
PATCHES="${SCRIPT_DIR}/raft_mesh"

if [ ! -d "${PATCHES}" ]; then
  echo "missing oracle patch directory: ${PATCHES}" >&2
  exit 1
fi

for src in "${PATCHES}"/*.js; do
  base="$(basename "${src}")"
  cp "${src}" "${APP_ROOT}/raft_mesh/${base}"
done

echo "oracle modules installed"
