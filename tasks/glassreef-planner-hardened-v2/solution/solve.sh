#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd /app
install -D "$SCRIPT_DIR/source/glassreef_planner.rs" /app/src/bin/glassreef_planner.rs
bash /app/scripts/run_glassreef_planner.sh
