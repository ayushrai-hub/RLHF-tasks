#!/bin/bash
mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

cd /app && cargo build --release 2>/dev/null
BUILD_RC=$?
if [ $BUILD_RC -ne 0 ]; then
    echo "Build failed with exit code $BUILD_RC"
    exit 0
fi

mkdir -p /app/output
/app/target/release/blind-signature-unlinkability --config-dir /app/config --data-file /app/data/transcript.json --output /app/output/verification_report.json || true

pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -v -rA

if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
