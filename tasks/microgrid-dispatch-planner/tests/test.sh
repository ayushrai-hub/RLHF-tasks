#!/bin/bash

# Python packages and the Rust toolchain are installed in environment/Dockerfile.
# No network access is required at runtime.

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script."
    exit 1
fi

_on_exit() {
    if [ ! -s /logs/verifier/ctrf.json ]; then
        echo '{"results":{"summary":{"passed":0,"failed":1,"pending":0,"skipped":0},"tests":[]}}' \
            > /logs/verifier/ctrf.json
    fi
}
trap _on_exit EXIT

python3 -m pytest -o cache_dir=/tmp/pytest_cache \
    --ctrf /logs/verifier/ctrf.json \
    /tests/test_outputs.py -v -rA --tb=short

if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
