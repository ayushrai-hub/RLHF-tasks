#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cp "$ROOT_DIR/internal/model/types.go" /app/internal/model/types.go
cp "$ROOT_DIR/internal/normalize/text.go" /app/internal/normalize/text.go
cp "$ROOT_DIR/internal/normalize/path.go" /app/internal/normalize/path.go
mkdir -p /app/internal/wire /app/internal/fold
cp "$ROOT_DIR/internal/wire/frame.go" /app/internal/wire/frame.go
cp "$ROOT_DIR/internal/fold/strings.go" /app/internal/fold/strings.go
mkdir -p /app/internal/clock /app/internal/bag
cp "$ROOT_DIR/internal/clock/stamp.go" /app/internal/clock/stamp.go
cp "$ROOT_DIR/internal/bag/map.go" /app/internal/bag/map.go
cp "$ROOT_DIR/internal/parse/load.go" /app/internal/parse/load.go
cp "$ROOT_DIR/internal/parse/kv.go" /app/internal/parse/kv.go
cp "$ROOT_DIR/internal/parse/inventory.go" /app/internal/parse/inventory.go
cp "$ROOT_DIR/internal/parse/auth.go" /app/internal/parse/auth.go
cp "$ROOT_DIR/internal/parse/web.go" /app/internal/parse/web.go
cp "$ROOT_DIR/internal/parse/history.go" /app/internal/parse/history.go
cp "$ROOT_DIR/internal/parse/persistence.go" /app/internal/parse/persistence.go
cp "$ROOT_DIR/internal/parse/network.go" /app/internal/parse/network.go
cp "$ROOT_DIR/internal/parse/audit.go" /app/internal/parse/audit.go
cp "$ROOT_DIR/internal/parse/deleted.go" /app/internal/parse/deleted.go
cp "$ROOT_DIR/internal/parse/git.go" /app/internal/parse/git.go
cp "$ROOT_DIR/internal/parse/secrets.go" /app/internal/parse/secrets.go
cp "$ROOT_DIR/internal/parse/archive.go" /app/internal/parse/archive.go
cp "$ROOT_DIR/internal/parse/configs.go" /app/internal/parse/configs.go
cp "$ROOT_DIR/internal/parse/process.go" /app/internal/parse/process.go
cp "$ROOT_DIR/internal/parse/containers.go" /app/internal/parse/containers.go
cp "$ROOT_DIR/internal/parse/strconv.go" /app/internal/parse/strconv.go
cp "$ROOT_DIR/internal/correlate/analyze.go" /app/internal/correlate/analyze.go
cp "$ROOT_DIR/internal/correlate/timeline.go" /app/internal/correlate/timeline.go
cp "$ROOT_DIR/internal/correlate/ioc.go" /app/internal/correlate/ioc.go
cp "$ROOT_DIR/internal/report/json.go" /app/internal/report/json.go
cp "$ROOT_DIR/internal/report/csv.go" /app/internal/report/csv.go
cp "$ROOT_DIR/internal/report/text.go" /app/internal/report/text.go
cp "$ROOT_DIR/internal/report/remediation.go" /app/internal/report/remediation.go

/usr/local/go/bin/gofmt -w /app/cmd/breach-ledger /app/internal
/usr/local/go/bin/go build -o /app/bin/breach-ledger /app/cmd/breach-ledger
