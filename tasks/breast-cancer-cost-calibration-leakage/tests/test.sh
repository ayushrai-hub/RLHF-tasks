#!/bin/bash
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt
if [ "$PWD" = "/" ]; then
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi
rm -rf /app/outputs
mkdir -p /app/outputs
Rscript --vanilla /app/analysis.R
python3 -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -v -rA
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
