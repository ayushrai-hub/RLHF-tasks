#!/bin/bash
# Oracle for milestone 3: forge a v0 admin token from the captured /reports token via
# a SHA-256 length-extension attack (no server key required).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/forge.go" /app/forge.go
cd /app
go build -o /app/forge /app/forge.go
/app/forge /app/captured.sigil /app/forged.sigil
