#!/usr/bin/env bash
# Post-edit hook: run Terminus validation when task files change
set -euo pipefail

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))" 2>/dev/null || echo "")

# Only validate Terminus task artifacts
case "$FILE_PATH" in
  */task.toml|*/instruction.md|*/environment/*|*/tests/*|*/solution/*|*/steps/*)
    ;;
  *)
    exit 0
    ;;
esac

# Find task root (directory containing task.toml)
TASK_DIR="$FILE_PATH"
while [[ "$TASK_DIR" != "/" && ! -f "$TASK_DIR/task.toml" ]]; do
  TASK_DIR="$(dirname "$TASK_DIR")"
done

if [[ ! -f "$TASK_DIR/task.toml" ]]; then
  exit 0
fi

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VALIDATOR="$REPO_ROOT/scripts/validate_task.py"

if [[ ! -f "$VALIDATOR" ]]; then
  exit 0
fi

export TASK_DIR
export VALIDATOR
python3 <<'PYEOF'
import json, os, subprocess, sys

task_dir = os.environ.get("TASK_DIR", "")
validator = os.environ.get("VALIDATOR", "")
if not task_dir or not validator:
    sys.exit(0)

proc = subprocess.run(
    [sys.executable, validator, task_dir],
    capture_output=True, text=True,
)
output = (proc.stdout or "") + (proc.stderr or "")
errors = sum(1 for line in output.splitlines() if line.startswith("ERROR:"))
if errors > 0:
    msg = (
        f"Terminus validation found {errors} error(s) in {task_dir}. "
        f"Run ./scripts/terminus validate for details.\n\n"
        + output[:2000]
    )
    print(json.dumps({"followup_message": msg}))
PYEOF
