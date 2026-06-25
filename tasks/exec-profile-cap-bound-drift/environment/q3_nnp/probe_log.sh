#!/bin/bash
set -euo pipefail
LOG="/app/work/nnp_probe.log"
mkdir -p /app/work
echo "nnp probe $(date -u +%s)" >> "$LOG"
