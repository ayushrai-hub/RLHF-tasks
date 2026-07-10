#!/bin/bash
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

cd /app && go build -o /app/bin/transitivity-checker ./cmd/transitivity-checker 2>/dev/null
BUILD_RC=$?
if [ $BUILD_RC -ne 0 ]; then
    echo "Build failed with exit code $BUILD_RC"
    exit $BUILD_RC
fi

mkdir -p /app/output
/app/bin/transitivity-checker data/rules.json output/results.json || true

pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -v -rA

if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
