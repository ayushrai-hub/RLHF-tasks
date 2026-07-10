#!/usr/bin/env bash
set -euo pipefail

GO_BIN="/usr/local/go/bin/go"
if [ ! -x "$GO_BIN" ]; then
    GO_BIN="$(command -v go)"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IN="/app/task_file/input_data"
OUT="/app/task_file/output_data"
mkdir -p "$OUT"

# Leave a standalone Go source under /app and build the graded deliverable from it.
cp "$SCRIPT_DIR/solve.go" /app/concrete_dispatch_solver.go
"$GO_BIN" build -o /tmp/concrete-dispatch-solver /app/concrete_dispatch_solver.go
/tmp/concrete-dispatch-solver "$IN" "$OUT"

# Self-validate against the authoritative model with the SAME floors the verifier
# enforces (raw >= 0.90, strict >= 0.83). Exit non-zero if the oracle regresses.
python3 - "$IN" "$OUT" <<'PYEOF'
import sys
sys.path.insert(0, "/app/task_file/scripts")
from model import evaluate
res = evaluate(sys.argv[1], sys.argv[2])
if res.get("penalty") or res.get("error"):
    print("oracle self-check FAILED:", res.get("penalty"), res.get("error"))
    sys.exit(1)
ok = res["total_score"] >= 0.90 and res["total_score_strict"] >= 0.83
print("oracle raw=%.4f strict=%.4f cement_conf=%.3f val=%.3f n=%d cement=%.3f fine=%.2f" % (
    res["total_score"], res["total_score_strict"], res["cement_conformance_score"],
    res["value_score"], res["assigned_count"], res["weighted_cement_pct"], res["weighted_fine_pct"]))
sys.exit(0 if ok else 1)
PYEOF
