#!/usr/bin/env bash
# Oracle sweep — requires Docker. Defaults to 1 parallel job (heavy).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! docker info >/dev/null 2>&1; then
  echo "✗ Docker daemon not running. Start Docker Desktop first." >&2
  exit 2
fi

JOBS=1
EXTRA=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --jobs|-j) JOBS="$2"; shift 2 ;;
    *) EXTRA+=("$1"); shift ;;
  esac
done

PY="${ROOT}/.venv-review/bin/python"
[ -x "$PY" ] || PY=python3

exec "$PY" "$ROOT/terminus/scripts/batch_runner.py" oracle \
  --jobs "$JOBS" \
  --output "$ROOT/jobs/batch-oracle-$(date +%Y%m%d-%H%M%S).json" \
  "${EXTRA[@]}"
