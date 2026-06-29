#!/usr/bin/env bash
set -u
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
APP_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$APP_DIR"
mkdir -p output
go run ./cmd/goadj \
  --rulebook u/tournament_rulebook.json \
  --policy j/policy.json \
  --record r/dragon-cup-17.ggr \
  --legacy r/legacy-1999.ggr \
  --out output/adjudication-proof.json
