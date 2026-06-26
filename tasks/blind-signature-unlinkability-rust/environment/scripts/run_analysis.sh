#!/bin/bash
set -e
cd /app
cargo build --release
mkdir -p /app/output
/app/target/release/blind-signature-unlinkability \
    --config-dir /app/config \
    --data-file /app/data/transcript.json \
    --output /app/output/verification_report.json
echo "Analysis complete. Report at /app/output/verification_report.json"
