#!/bin/bash
set -o pipefail

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

if [ "$PWD" = "/" ]; then
  cd /app
fi

python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_m1.py -rA

if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
