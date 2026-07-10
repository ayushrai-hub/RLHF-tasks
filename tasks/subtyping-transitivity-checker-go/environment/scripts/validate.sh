#!/bin/bash
set -e
cd /app
echo "Building..."
go build -o bin/transitivity-checker ./cmd/transitivity-checker
echo "Running analysis..."
./bin/transitivity-checker data/rules.json output/results.json
echo "Validating output..."
python3 -c "import json; d=json.load(open('output/results.json')); print(f'Rules: {d[\"total_rules\"]}, Obligations: {len(d[\"obligations\"])}')"
echo "Done."
