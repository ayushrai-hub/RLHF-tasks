#!/usr/bin/env bash
set -uo pipefail

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
printf '{"version":"1.0.0","results":[]}\n' > /logs/verifier/ctrf.json

if [ "$PWD" = "/" ] || [ -z "${PWD:-}" ]; then
  echo "Error: No working directory set. Please set WORKDIR in your Dockerfile before running this script." >&2
  echo 0 > /logs/verifier/reward.txt
  exit 1
fi

export PATH="/usr/local/cargo/bin:/opt/verifier-venv/bin:/usr/local/bin:${PATH}"
TEST_DIR="${TEST_DIR:-/tests}"

set +e
bash /app/scripts/reset-state.sh
RESET_RC=$?
cd /app && cargo build --release --locked -p ballctl
BUILD_RC=$?
if [ "$BUILD_RC" -eq 0 ]; then
  install -m 0755 /app/target/release/ballctl /usr/local/bin/ballctl
fi
/opt/verifier-venv/bin/python3 -m pytest -o cache_dir=/tmp/pytest_cache \
  --ctrf /logs/verifier/ctrf.json "${TEST_DIR}/test_outputs.py" -rA
PYTEST_RC=$?

[ "$RESET_RC" -eq 0 ] && [ "$BUILD_RC" -eq 0 ] && [ "$PYTEST_RC" -eq 0 ]
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
