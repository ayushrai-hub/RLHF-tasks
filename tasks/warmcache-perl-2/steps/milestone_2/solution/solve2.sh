#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/plan.pl" /app/plan.pl
mkdir -p /app/out
perl /app/plan.pl reconcile
echo "milestone 2: wrote /app/out/reconcile.json"
