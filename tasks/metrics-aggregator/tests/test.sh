#!/bin/bash
# Note: -e intentionally omitted — exit codes are captured manually below
set -uo pipefail
export PATH="/usr/local/cargo/bin:$PATH"

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Set WORKDIR in Dockerfile."
    mkdir -p /logs/verifier
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

mkdir -p /logs/verifier
mkdir -p /app/output

cd /app && cargo build --release 2>&1
BUILD_RC=$?
if [ $BUILD_RC -ne 0 ]; then
    echo "Build failed with exit code $BUILD_RC"
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -v -rA

if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
