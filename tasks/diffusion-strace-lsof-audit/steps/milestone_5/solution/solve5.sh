#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORACLE_KT="$SCRIPT_DIR/kotlin"
STAGE="$SCRIPT_DIR/stage_kotlin.sh"
bash "$STAGE" "$ORACLE_KT" OpA ReconcileB PhaseC StepD
cp "$ORACLE_KT/OpA.kt" /app/q7harvest/src/main/kotlin/io/q7desk/op/OpA.kt
cp "$ORACLE_KT/ReconcileB.kt" /app/q8strace/src/main/kotlin/io/q7desk/reconcile/ReconcileB.kt
cp "$ORACLE_KT/PhaseC.kt" /app/q9lsof/src/main/kotlin/io/q7desk/phase/PhaseC.kt
cp "$ORACLE_KT/StepD.kt" /app/r4policy/src/main/kotlin/io/q7desk/step/StepD.kt
python3 "$SCRIPT_DIR/repair_runbooks.py"
bash /app/scripts/build_all.sh
bash /app/scripts/milestone_probes.sh clean
