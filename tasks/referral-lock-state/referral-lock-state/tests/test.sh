#!/bin/bash
set -euo pipefail
APP_DIR=${APP_DIR:-/app}
LOGS_DIR=${LOGS_DIR:-/logs}
TESTS_DIR=${TESTS_DIR:-/tests}
mkdir -p "$LOGS_DIR/verifier"
python3 "$APP_DIR/reconcile.py"
if python3 -m pytest "$TESTS_DIR/test_outputs.py" -q -rA; then
  echo 1 > "$LOGS_DIR/verifier/reward.txt"
  exit 0
fi
echo 0 > "$LOGS_DIR/verifier/reward.txt"
exit 1
