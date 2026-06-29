#!/bin/bash
if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set." >&2
    exit 1
fi

mkdir -p /logs/verifier

/opt/verifier-venv/bin/python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -v -rA
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
