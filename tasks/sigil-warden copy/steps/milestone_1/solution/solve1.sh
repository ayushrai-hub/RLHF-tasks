#!/bin/bash
# Oracle for milestone 1: build the warden checker (its verify subcommand).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/warden.go" /app/warden.go
cd /app
go build -o /app/warden /app/warden.go
