#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier

python -m pytest -p no:cacheprovider /tests/test_m1.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
