#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier

if [ "$PWD" = "/" ]; then
  echo "Error: No working directory set."
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

/opt/venv/bin/python -m pytest \
  -o cache_dir=/tmp/fleet-risk-calibrator-pytest-cache \
  --ctrf /logs/verifier/ctrf.json \
  /tests/test_outputs.py \
  -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
