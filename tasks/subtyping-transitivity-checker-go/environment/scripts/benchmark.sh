#!/bin/bash
# Benchmark the transitivity checker with the default rule set
set -e
cd /app
echo "Building..."
go build -o bin/transitivity-checker ./cmd/transitivity-checker
echo "Running analysis..."
time ./bin/transitivity-checker data/rules.json /tmp/bench_output.json
echo "Done. Output:"
cat /tmp/bench_output.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'Rules: {d[\"total_rules\"]}, Obligations: {len(d[\"obligations\"])}')"
