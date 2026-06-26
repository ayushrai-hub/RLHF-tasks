#!/bin/bash
# Oracle for milestone 3: the warden binary now also handles third-party caveats,
# discharge, and bind.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/warden.go" /app/warden.go
cd /app
go build -o /app/warden /app/warden.go
