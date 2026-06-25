#!/usr/bin/env bash
set -uo pipefail

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
printf '%s\n' '{"version":"1.0.0","results":{"summary":{"tests":0,"passed":0,"failed":0,"pending":0,"skipped":0,"other":0}}}}' > /logs/verifier/ctrf.json
TEST_DIR="${TEST_DIR:-/tests}"
export PATH="/usr/local/cargo/bin:/app/bin:${PATH}"
export MAVLINK_TEST_FIXTURES="${MAVLINK_TEST_FIXTURES:-/tmp/mavlink-mseq-fixtures/logs}"
mkdir -p "${MAVLINK_TEST_FIXTURES}"

if [ "$PWD" = "/" ] || [ "$PWD" != "/app" ]; then
  echo "Error: working directory must be /app (got: ${PWD})." >&2
  echo 0 > /logs/verifier/reward.txt
  exit 0
fi

set +e
if [[ -x /app/scripts/build.sh ]]; then
  /app/scripts/build.sh
else
  true
fi
if [ $? -eq 0 ]; then
  /opt/verifier-venv/bin/python "${TEST_DIR}/gen_mseq_fixtures.py"
  /opt/verifier-venv/bin/python -m pytest "${TEST_DIR}/test_outputs.py" -rA \
    --ctrf "/logs/verifier/ctrf.json"
else
  false
fi
if [ $? -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
