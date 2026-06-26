#!/usr/bin/env bash

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

STATUS=0

PYTHON_BIN="/opt/verifier-venv/bin/python"
if [ ! -x "$PYTHON_BIN" ]; then
    PYTHON_BIN="/usr/bin/python3"
fi

"$PYTHON_BIN" -m pytest -q /tests/test_outputs.py -rA || STATUS=1

[ "$STATUS" -eq 0 ]
rc=$?
if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
