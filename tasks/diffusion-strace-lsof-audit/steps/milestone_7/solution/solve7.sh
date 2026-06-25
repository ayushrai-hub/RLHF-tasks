#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORACLE="$SCRIPT_DIR/oracle"
STAGE="$SCRIPT_DIR/stage_kotlin.sh"
bash "$STAGE" "$ORACLE" ReconcileB PhaseC
cp "$ORACLE/ReconcileB.kt" /app/q8strace/src/main/kotlin/io/q7desk/reconcile/ReconcileB.kt
cp "$ORACLE/PhaseC.kt" /app/q9lsof/src/main/kotlin/io/q7desk/phase/PhaseC.kt
python3 "$SCRIPT_DIR/repair_relay_lane.py"
bash /app/scripts/build_all.sh
bash /app/scripts/milestone_probes.sh verify
