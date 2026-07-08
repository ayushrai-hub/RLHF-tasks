#!/bin/bash
set -euo pipefail
OUTDIR="${1:-/app/output}"
exec /app/.venv/bin/python3 /app/scripts/driver.py "$OUTDIR"
