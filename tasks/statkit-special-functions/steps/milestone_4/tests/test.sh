#!/bin/bash
set -uo pipefail

# Verifier dependencies (pytest, pytest-json-ctrf) are baked into the image at
# /opt/verifier-venv. No network or installs happen here.

# Canonical working-directory guard.
if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    mkdir -p /logs/verifier
    echo 0 > /logs/verifier/reward.txt
    exit 1
fi

TEST_DIR="${TEST_DIR:-/tests}"
mkdir -p /logs/verifier

# Restore the verifier-owned frozen C acceptance suite and sample fixtures so an
# agent cannot pass by editing them.
if [ -d /opt/golden/tests ]; then
    rm -rf /app/tests
    mkdir -p /app/tests
    cp -a /opt/golden/tests/. /app/tests/
fi
if [ -d /opt/golden/data ]; then
    rm -rf /app/data
    mkdir -p /app/data
    cp -a /opt/golden/data/. /app/data/
fi

python -m pytest \
    -o cache_dir=/tmp/pytest_cache \
    --ctrf /logs/verifier/ctrf.json \
    "$TEST_DIR/test_m4.py" -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
