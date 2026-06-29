#!/bin/bash
set -uo pipefail

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    mkdir -p /logs/verifier
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

mkdir -p /logs/verifier
python -m pip install --break-system-packages --no-index --find-links /tests/wheels pytest==8.4.1 pytest-json-ctrf==0.3.5 >/dev/null
python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_m3.py -rA
rc=$?
if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
