#!/bin/bash
set -uo pipefail

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

ensure_reward_written() {
    if [ ! -f /logs/verifier/reward.txt ]; then
        echo 0 > /logs/verifier/reward.txt
    fi
}
trap ensure_reward_written EXIT INT TERM

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    exit 1
fi

TEST_DIR="${TEST_DIR:-/tests}"
set +e
python3 -m pytest -o cache_dir=/tmp/pytest_cache \
    --ctrf /logs/verifier/ctrf.json "${TEST_DIR}/test_m2.py" -rA
rc=$?

if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
