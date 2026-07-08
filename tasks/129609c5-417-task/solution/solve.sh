#!/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$HERE/source/analytics.tcl" /app/src/analytics.tcl

bash /app/scripts/start_service.sh
echo "Oracle applied"
