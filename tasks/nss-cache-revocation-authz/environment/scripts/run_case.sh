#!/bin/bash
set -euo pipefail
cd /app/environment
make build
mkdir -p /app/output /app/work/authz-state
./bin/authzctl run-case --case "${1:-fixtures/cases/desk-basic.json}" --state /app/work/authz-state --out /app/output/authorization-trace.json
