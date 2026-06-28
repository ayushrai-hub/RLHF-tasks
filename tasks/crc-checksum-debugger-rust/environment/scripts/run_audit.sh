#!/bin/bash
set -euo pipefail
cd /app
cargo build --release 2>&1
mkdir -p /app/output
./target/release/relay-audit \
    --config config/relay.toml \
    --journal data/journal.json \
    --output output/report.json
echo "Audit complete."
