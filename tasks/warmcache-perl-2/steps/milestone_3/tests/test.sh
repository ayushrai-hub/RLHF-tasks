#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
TEST_DIR="${TEST_DIR:-/tests}"
if [ "$PWD" = "/" ]; then
  echo "Error: No working directory set."
  cat > /logs/verifier/ctrf.json <<'JSON'
{"results":{"tool":{"name":"pytest"},"summary":{"tests":0,"passed":0,"failed":0,"pending":0,"skipped":0,"other":0,"start":0,"stop":0},"tests":[]}}
JSON
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi
python3 -m pytest --ctrf /logs/verifier/ctrf.json "$TEST_DIR/test_m3.py" -rA
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
