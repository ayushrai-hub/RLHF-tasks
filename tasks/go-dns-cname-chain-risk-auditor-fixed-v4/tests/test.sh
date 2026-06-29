#!/usr/bin/env bash
set -uo pipefail

mkdir -p /logs/verifier /logs/artifacts
echo 0 > /logs/verifier/reward.txt
touch /logs/artifacts/.keep

if [ "$PWD" = "/" ]; then
    echo "Error: No WORKDIR set in Dockerfile." >&2
    exit 1
fi

cd /app
python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
