#!/bin/bash
set -euo pipefail
LOG="/app/work/step_log.txt"
mkdir -p /app/work
echo "step mark=${1:-} stamp=${2:-}" >> "$LOG"
