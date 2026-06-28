#!/bin/bash
set -euo pipefail
cd /app
cargo build --release 2>&1
./target/release/relay-audit \
    --config config/relay.toml \
    --journal data/journal.json \
    --output output/report.json
python3 -c "
import json
with open('output/report.json') as f:
    r = json.load(f)
s = r['summary']
print(f'Packets: {s[\"total_packets\"]}')
print(f'Pass: {s[\"reconciled_pass\"]}, Fail: {s[\"reconciled_fail\"]}')
print(f'Avg drift: {s[\"avg_drift\"]}')
"
