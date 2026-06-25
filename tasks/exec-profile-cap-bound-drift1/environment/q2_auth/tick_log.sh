#!/bin/bash
set -euo pipefail
LOG="/app/work/auth_tick.log"
mkdir -p /app/work
echo "$(date -u +%s) tick actor=${1:-}" >> "$LOG"
