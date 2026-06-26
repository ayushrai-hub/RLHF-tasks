#!/bin/bash
TASK="$(cd "$(dirname "$0")/.." && pwd)"
OR="$TASK/solution/oracle"
ENV="$TASK/environment"
OUT="$TASK/solution/oracle_clean.patch"
rm -f "$OUT"
python3 "$TASK/scripts/gen_oracle_patch.py"
