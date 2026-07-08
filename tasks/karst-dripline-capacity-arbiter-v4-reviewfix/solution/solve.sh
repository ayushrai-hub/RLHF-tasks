#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd /app
cp "$SCRIPT_DIR/dripline_solution_impl.go" /app/cmd/dripline/main.go
gofmt -w /app/cmd/dripline/main.go
go run ./cmd/dripline --input /app/input --output /app/output/dripline_report.json
