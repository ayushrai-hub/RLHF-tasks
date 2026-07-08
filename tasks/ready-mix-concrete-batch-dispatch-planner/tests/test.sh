#!/usr/bin/env bash
TEST_STATUS=0
trap 'exit $TEST_STATUS' EXIT

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set." >&2
    exit 1
fi

python3 -c "import pytest, pytest_jsonreport" || {
    echo "Pre-installed test dependencies missing; Dockerfile build is broken" >&2
    exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 -m pytest "$SCRIPT_DIR/test_outputs.py" -v -rA --tb=short   --json-report --json-report-file=/logs/verifier/test_report.json
TEST_STATUS=$?

(exit $TEST_STATUS)
if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
