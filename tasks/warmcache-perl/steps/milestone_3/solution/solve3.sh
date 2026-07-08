#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/plan.pl" /app/plan.pl
mkdir -p /app/out
perl /app/plan.pl digest
echo "milestone 3: wrote /app/out/digest.json"
