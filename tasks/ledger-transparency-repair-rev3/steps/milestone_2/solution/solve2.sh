#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/files/ledger_verify.c" /app/native/ledger_verify.c
make -C /app/native -B
