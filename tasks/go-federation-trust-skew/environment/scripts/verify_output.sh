#!/usr/bin/env bash
set -euo pipefail
mkdir -p /app/output/stage /app/output/harness
cd /app/environment
go test ./internal/ward/ -run TestWard_ProbeFresh -count=1 >/dev/null
/app/bin/probe
go test ./internal/ward/ -run 'TestWard_T01|TestWard_T10|TestWard_T18|TestWard_T26' -count=1 >/tmp/ward-sample.txt 2>&1
cp /tmp/ward-sample.txt /app/output/harness/sample.txt
if grep -q '--- FAIL:' /tmp/ward-sample.txt; then
  echo "harness_fail" > /app/output/harness/status.txt
  exit 1
fi
echo "harness_ok" > /app/output/harness/status.txt
