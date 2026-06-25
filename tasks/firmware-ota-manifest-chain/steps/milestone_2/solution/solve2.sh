#!/bin/bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp -R "${SCRIPT_DIR}/files/src/"* "${APP_ROOT}/src/"
/app/bin/oracle-build-ota.sh
