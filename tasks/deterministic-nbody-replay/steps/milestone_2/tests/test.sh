#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
pip3 install --no-cache-dir --break-system-packages --no-index --find-links /opt/test-deps/ pytest==9.1.1 pytest-json-ctrf==0.3.5 -q
set +e
python3 -m pytest -o cache_dir=/tmp/pytest_cache --ctrf /logs/verifier/ctrf.json /tests/test_m2.py -rA
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
