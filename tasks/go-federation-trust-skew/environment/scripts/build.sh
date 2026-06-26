#!/usr/bin/env bash
set -euo pipefail
cd /app/environment
go build -o /app/bin/probe ./cmd/probe
go build -o /app/bin/daemon ./cmd/daemon
go build ./...
