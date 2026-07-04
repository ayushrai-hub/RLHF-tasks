#!/bin/bash
set -euo pipefail
PLAN="${1:-/app/environment/configs/public-plan.json}"
OUT="${2:-/app/output/search-run.json}"
cd /app/environment
go run ./cmd/offline-search search --plan "$PLAN" --out "$OUT"
