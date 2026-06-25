#!/bin/bash
set -euo pipefail
LOG="/app/work/launch_probe.log"
mkdir -p /app/work
echo "probe mark=${1:-} round=${2:-}" >> "$LOG"
