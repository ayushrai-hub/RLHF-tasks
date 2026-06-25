#!/bin/bash
mkdir -p /logs/verifier

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set."
    exit 1
fi

pip install --quiet --no-cache-dir --no-index --find-links /opt/test-wheels \
    pytest==8.4.1 pytest-json-ctrf==0.3.5 JPype1==1.5.0 jaydebeapi==1.2.3

python3 -m pytest \
    -o cache_dir=/tmp/pytest_cache \
    --ctrf /logs/verifier/ctrf.json \
    /tests/test_m3.py -rA
RC=$?
if [ "$RC" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
