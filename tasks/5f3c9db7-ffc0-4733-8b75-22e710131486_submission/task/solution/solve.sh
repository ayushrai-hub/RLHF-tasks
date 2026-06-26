#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PATH="/usr/local/go/bin:${PATH}"

bash "${SCRIPT_DIR}/apply_patch.sh"

go build -C /app/environment -o /app/logrecover /app/environment/cmd/logrecover
mkdir -p /app/output
/app/logrecover \
  --pack /app/fixtures/scenarios/pack.json \
  --out /app/output/recovery_report.json
