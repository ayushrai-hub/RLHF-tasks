#!/bin/bash
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

set -uo pipefail

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile before running this script." >&2
    exit 1
fi

if ! bash /app/scripts/start_api.sh; then
    echo "start_api failed; leaving reward=0" >&2
    exit 1
fi
if ! bash /app/bin/ipaudit.sh fetch; then
    echo "ipaudit.sh fetch failed; leaving reward=0" >&2
    exit 1
fi
if ! bash /app/bin/ipaudit.sh normalize; then
    echo "ipaudit.sh normalize failed; leaving reward=0" >&2
    exit 1
fi

pytest --ctrf /logs/verifier/ctrf.json /tests/test_m1.py -rA
status=$?

if [ $status -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
