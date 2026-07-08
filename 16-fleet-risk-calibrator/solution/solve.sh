#!/bin/bash
set -euo pipefail

cp /solution/features.go /app/internal/features/features.go
cp /solution/score.go /app/internal/model/score.go
cp /solution/run.go /app/internal/app/run.go

cd /app
gofmt -w /app/internal/features/features.go /app/internal/model/score.go /app/internal/app/run.go
go test ./...
go run ./cmd/fleetrisk \
  --model /app/config/model.json \
  --policy /app/config/policy.json \
  --calls /app/data/service_calls.csv \
  --windows /app/data/sensor_windows.csv \
  --history /app/data/asset_history.csv \
  --labels /app/data/maintenance_labels.csv \
  --capacity /app/data/site_capacity.csv \
  --out-dir /app/out
