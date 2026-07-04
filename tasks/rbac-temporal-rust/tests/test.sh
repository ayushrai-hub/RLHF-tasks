#!/bin/bash
# Verifier for the temporal RBAC task.
# Runs the Rust integration suites (visible + hidden), captures their output,
# then uses pytest to assert the suites actually compiled, ran, and passed.
# pytest is pre-installed in the image, so no network access or package
# installation happens here.

set -uo pipefail

mkdir -p /logs/verifier
echo 0 > /logs/verifier/reward.txt

if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set."
    exit 1
fi

# Install the canonical test suites regardless of any copy present in the image,
# so an agent cannot weaken the graded tests.
mkdir -p /app/tests
cp /tests/test_rbac.rs /app/tests/test_rbac.rs
cp /tests/test_rbac_hidden.rs /app/tests/test_rbac_hidden.rs

# Run the full Rust test set and capture the output for inspection.
# --no-fail-fast ensures every test binary runs even if an earlier one fails, so
# the log always reflects the complete picture. A per-command timeout bounds a
# hung compile or test independently of the outer verifier timeout; if it fires,
# the log lacks a passing summary and the reward stays 0.
cd /app
timeout 240 cargo test --offline --no-fail-fast -- --nocapture > /logs/verifier/cargo_test.log 2>&1
cat /logs/verifier/cargo_test.log

# Validate the captured cargo output through pytest (this is the reward gate).
PYTHONPATH=/app pytest -p no:cacheprovider --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA

rc=$?
if [ "$rc" -eq 0 ]; then
    echo 1 > /logs/verifier/reward.txt
else
    echo 0 > /logs/verifier/reward.txt
fi
