#!/usr/bin/env bash
# Build the gomvs binary at /app/gomvs.
set -euo pipefail
cd /app
go build -o /app/gomvs .
echo "built /app/gomvs"
