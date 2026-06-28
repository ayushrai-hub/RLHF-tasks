#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/clinicflow_cli_m3.py" /app/clinicflow/cli.py
python -m clinicflow actions
