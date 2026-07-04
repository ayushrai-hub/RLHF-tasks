#!/bin/bash
set -euo pipefail

mkdir -p /logs/verifier

# Activate the pre-baked verifier virtualenv. The verifier phase has no network
# (allow_internet=false), so nothing is installed here; the venv was built into
# the image at build time. The test logic lives in /tests, mounted only now.
export VIRTUAL_ENV=/opt/verifier-venv
export PATH="$VIRTUAL_ENV/bin:$PATH"

set +e
python -m pytest -p no:cacheprovider --ctrf /logs/verifier/ctrf.json /tests/test_m4.py -rA
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
