#!/bin/bash
set -uo pipefail

export PATH="/usr/local/cargo/bin:$PATH"

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

if [ "$PWD" = "/" ]; then
  echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
  echo 0 > /logs/verifier/reward.txt
  exit 1
fi

TEST_DIR="${TEST_DIR:-/tests}"
python3 -m pytest -o cache_dir=/tmp/pytest_cache \
  --ctrf /logs/verifier/ctrf.json "$TEST_DIR/test_outputs.py" -rA
TEST_RESULT=$?

if [ "$TEST_RESULT" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
