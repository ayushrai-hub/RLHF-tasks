#!/usr/bin/env bash
# Parallel validate across all discovered tasks.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${ROOT}/.venv-review/bin/python"
[ -x "$PY" ] || PY=python3
exec "$PY" "$ROOT/terminus/scripts/batch_runner.py" validate \
  --output "$ROOT/jobs/batch-validate-$(date +%Y%m%d-%H%M%S).json" \
  "$@"
