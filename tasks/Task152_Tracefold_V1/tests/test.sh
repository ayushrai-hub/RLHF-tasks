#!/usr/bin/env bash
set -Eeuo pipefail

# Verifier dependencies are installed in environment/Dockerfile.
# Add task-specific verifier-only Python packages there, not here.

mkdir -p /logs/verifier

if [ "$PWD" = "/" ]; then exit 1; fi
echo 0 > /logs/verifier/reward.txt

cd /app
set +e
cargo build --release --locked --offline
python -m pytest -o cache_dir=/tmp/pytest_cache --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
