#!/bin/bash

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

/app/bin/start_registry.sh || true

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set."
    false
else
    /opt/verifier/bin/python -m pytest         -o cache_dir=/tmp/pytest_cache         --ctrf /logs/verifier/ctrf.json         /tests/test_m3.py -rA
fi

if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
