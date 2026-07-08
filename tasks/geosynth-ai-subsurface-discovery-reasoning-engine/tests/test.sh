#!/usr/bin/env bash
set -euo pipefail

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

if [ "$PWD" = "/" ]; then
echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile."
exit 1
fi

# rebuild-geosynth-engine.sh runs inside pytest via tests/conftest.py before behavioral cases

set +e
/opt/verifier-venv/bin/python3 -m pytest \
  -rA \
  -o cache_dir=/tmp/pytest_cache \
  --ctrf /logs/verifier/ctrf.json \
  /tests/test_outputs.py
rc=$?
if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
