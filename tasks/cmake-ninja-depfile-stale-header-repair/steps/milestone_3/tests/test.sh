#!/bin/bash

trap '[[ -f /logs/verifier/reward.txt ]] || { mkdir -p /logs/verifier && echo 0 > /logs/verifier/reward.txt; }' EXIT

set -euo pipefail
mkdir -p /logs/verifier

if [ "${PWD:-/}" = "/" ]; then
  echo "Error: No working directory set. Set WORKDIR in the Dockerfile (e.g. /app)." >&2
  exit 1
fi

set +e
/opt/verifier-venv/bin/python -m pytest \
  -o cache_dir=/tmp/pytest_cache \
  --ctrf /logs/verifier/ctrf.json \
  /tests/test_m3.py -rA
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
