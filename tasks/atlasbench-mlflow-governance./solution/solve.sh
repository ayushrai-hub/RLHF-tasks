#!/usr/bin/env bash
set -euo pipefail

cd /app/atlas-harden
cp /solution/engine.go /app/atlas-harden/engine.go
go build -o /app/bin/atlas-harden .

/app/bin/atlas-harden \
  --dossier /app/data/governance-dossier.md \
  --config-dir /app/data/configs \
  --out-dir /app/output/configs \
  --evidence /app/output/evidence.db
