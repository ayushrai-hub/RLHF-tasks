#!/bin/bash
set -uo pipefail
export PATH="/usr/local/go/bin:$PATH"

if [ "$PWD" = "/" ]; then
    mkdir -p /logs/verifier
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

mkdir -p /logs/verifier

cd /app && go build -o bin/rate-limiter ./cmd/limiter 2>&1
BUILD_RC=$?
if [ $BUILD_RC -ne 0 ]; then
    echo "Build failed"
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

mkdir -p /app/output
/app/bin/rate-limiter analyze --traffic /app/data/traffic --output /app/output --format both || true

python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -v -rA

if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
