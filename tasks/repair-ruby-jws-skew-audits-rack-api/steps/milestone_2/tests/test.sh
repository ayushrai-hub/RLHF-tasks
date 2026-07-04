#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier && echo 0 > /logs/verifier/reward.txt
trap 'sync /logs/verifier 2>/dev/null || true; sleep 0.25' EXIT

if [ "$PWD" = "/" ]; then
  echo "Error: No working directory set." >&2
  exit 1
fi

[ -d /workspace ] || { echo "ERROR: /workspace not found." >&2; exit 1; }

if ! curl -sf "http://127.0.0.1:8966/health" >/dev/null 2>&1; then
  /workspace/scripts/start-stampgate-api.sh
fi

python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_m2.py -rA
exit_code=$?

if [ "$exit_code" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
