#!/usr/bin/env bash
set -u

HERE="$(cd "$(dirname "$0")" && pwd)"
mkdir -p /logs/verifier
cd /app || exit 1

python3 -m pytest --ctrf /logs/verifier/ctrf.json "$HERE/test_outputs.py" -rA
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
