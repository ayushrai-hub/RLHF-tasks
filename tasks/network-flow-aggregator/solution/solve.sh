#!/usr/bin/env bash
# Solution script for network-flow-aggregator
# Fixes bugs across all 4 library crates

set -euo pipefail

if [ ! -d "/app" ]; then
    echo "Error: /app not found"
    exit 1
fi

# Fix parse stage: Remove all conditional bug blocks and mutable statics
cp /solution/fixed/parse_lib.rs /app/parse/src/lib.rs

# Fix aggregate stage: Remove cross-module contamination and dual-condition bugs
cp /solution/fixed/aggregate_lib.rs /app/aggregate/src/lib.rs

# Fix classify stage: Remove risk score inflation and category misclassification
cp /solution/fixed/classify_lib.rs /app/classify/src/lib.rs

# Fix emit stage: Remove conditional aggregate drops and flow underflow
cp /solution/fixed/emit_lib.rs /app/emit/src/lib.rs

# Rebuild the workspace
cd /app

# Force rebuild by touching all source files
find . -name "*.rs" -exec touch {} +

# Clean and rebuild with offline mode
rm -rf target/release/nfa_verify target/release/.fingerprint/nfa_verify*
CARGO_NET_OFFLINE=true cargo build --workspace --release --offline 2>&1
if [ $? -ne 0 ]; then
    echo "Error: cargo build failed"
    exit 1
fi

echo "Build complete"

# Copy binary to expected location
cp target/release/nfa_verify /app/nfa_verify

# Run the verifier to produce the report
mkdir -p /tmp
/app/nfa_verify /app/traces/sample_trace.csv /tmp/test_report.json

echo "Solution applied successfully"
