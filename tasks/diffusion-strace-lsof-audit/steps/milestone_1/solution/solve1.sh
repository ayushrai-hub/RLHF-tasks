#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORACLE="$SCRIPT_DIR/oracle"
STAGE="$SCRIPT_DIR/stage_kotlin.sh"
bash "$STAGE" "$ORACLE" OpA
cp "$ORACLE/OpA.kt" /app/q7harvest/src/main/kotlin/io/q7desk/op/OpA.kt
bash /app/scripts/build_all.sh
bash /app/scripts/milestone_probes.sh index
