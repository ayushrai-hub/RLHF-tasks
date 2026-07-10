#!/bin/bash

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Set WORKDIR in Dockerfile."
    mkdir -p /logs/verifier
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

mkdir -p /logs/verifier

export PATH="/usr/local/go/bin:$PATH"

cd /app && go build -o /app/bin/pubsub-validator ./cmd/pubsub-validator 2>&1
BUILD_RC=$?
if [ $BUILD_RC -ne 0 ]; then
    echo "Build failed with exit code $BUILD_RC"
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

mkdir -p /app/output
/app/bin/pubsub-validator --data /app/data/delivery_log.json --config /app/config/pubsub.toml --output /app/output || true

python3 -m pytest -o cache_dir=/tmp/pytest_cache \
    --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -v -rA

if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
