#!/bin/bash
set -euo pipefail

export PATH="/usr/local/go/bin:${PATH}"

cd /app

cp /solution/internal/codec/codec.go /app/internal/codec/codec.go
cp /solution/internal/quota/engine.go /app/internal/quota/engine.go
cp /solution/internal/legacy/legacy.go /app/internal/legacy/legacy.go
cp /solution/internal/projection/projection.go /app/internal/projection/projection.go
cp /solution/internal/journal/journal.go /app/internal/journal/journal.go

GONOSUMDB='*' GOFLAGS='-mod=mod' go build -o /app/bin/ledgerctl /app/cmd/ledgerctl

rm -rf /app/state/journal /app/state/projection.json /app/state/checkpoint.json
mkdir -p /app/state/journal/batches /app/output

/app/bin/ledgerctl import --batch seed --events /app/data/batches/seed.jsonl
/app/bin/ledgerctl rebuild
/app/bin/ledgerctl report --out /app/output/quota_report.json
/app/bin/ledgerctl audit --out /app/output/audit_trail.json

test -s /app/output/quota_report.json
test -s /app/output/audit_trail.json
