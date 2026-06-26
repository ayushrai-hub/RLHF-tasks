#!/bin/bash
# Oracle for milestone 2: the same warden binary now also mints and attenuates.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/warden.go" /app/warden.go
cd /app
go build -o /app/warden /app/warden.go
