#!/usr/bin/env bash

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

# Pre-write minimal CTRF so the platform never sees verifier_did_not_run
cat > /logs/verifier/ctrf.json << 'CTRF'
{"results":{"tool":{"name":"pytest"},"summary":{"tests":0,"passed":0,"failed":0,"pending":0,"skipped":0,"other":0},"tests":[]}}
CTRF

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set."
    exit 1
fi

cd /app

# Always rebuild from source to ensure Rust code was actually fixed
# This prevents agents from bypassing the task by writing JSON directly
CARGO_NET_OFFLINE=true cargo build --release --offline 2>&1
if [ $? -ne 0 ]; then
    echo "Error: cargo build failed"
    exit 1
fi

# Remove any pre-existing report to force binary execution
rm -f /tmp/test_report.json

# Run the rebuilt binary to generate the report
/app/target/release/nfa_verify /app/traces/sample_trace.csv /tmp/test_report.json
assert_exit_code=$?

if [ "$assert_exit_code" -ne 0 ]; then
    echo "Error: nfa_verify binary failed with exit code $assert_exit_code"
    exit 1
fi

# Verify the report was actually created by the binary
if [ ! -f /tmp/test_report.json ]; then
    echo "Error: /tmp/test_report.json not created by binary"
    exit 1
fi

pytest --ctrf /logs/verifier/ctrf.json "${TEST_DIR:-/tests}/test_outputs.py" -rA -v

if [ $? -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
