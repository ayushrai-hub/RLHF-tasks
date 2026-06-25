#!/bin/bash
if [ "$(pwd)" != "/app" ]; then cd /app; fi
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

python -m pytest \
    -o cache_dir=/tmp/pytest_cache \
    --ctrf /logs/verifier/ctrf.json \
    /tests/test_m1.py -rA
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
