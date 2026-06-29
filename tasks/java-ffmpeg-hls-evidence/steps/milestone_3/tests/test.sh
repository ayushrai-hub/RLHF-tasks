#!/bin/bash
mkdir -p /logs/verifier

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set."
    exit 1
fi

# Activate the build-time venv that already has pytest + jaydebeapi etc.
# installed (see Dockerfile: /opt/test-venv). No runtime pip install needed.
source /opt/test-venv/bin/activate

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
