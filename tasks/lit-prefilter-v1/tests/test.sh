#!/bin/bash
# Verifier deps (pytest, pytest-json-ctrf, the Go toolchain) are baked into
# environment/Dockerfile. Nothing is installed at runtime; the tests only
# compile and run the litpre binary from /app.
set -uo pipefail

mkdir -p /logs/verifier

TEST_PATH="${TEST_PATH:-/tests/test_outputs.py}"

python3 -m pytest -o cache_dir=/tmp/pytest_cache --ctrf /logs/verifier/ctrf.json "$TEST_PATH" -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
