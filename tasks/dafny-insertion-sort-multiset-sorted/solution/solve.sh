#!/usr/bin/env bash
set -euo pipefail
cp /solution/solution_correct.dfy /app/solution.dfy
bash /app/verify.sh
