#!/usr/bin/env bash
# One-shot setup for Terminus review tooling (host or review container).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --check-only) CHECK_ONLY=1 ;;
  esac
done

echo "=== Terminus review setup ==="

VENV="$ROOT/.venv-review"
if [ ! -d "$VENV" ]; then
  echo "Creating review venv at .venv-review ..."
  python3 -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"

if [ -f "$ROOT/requirements.txt" ]; then
  echo "Installing Python deps from requirements.txt..."
  pip install --upgrade pip >/dev/null 2>&1 || true
  pip install -r "$ROOT/requirements.txt"
else
  echo "! requirements.txt not found at repo root"
fi

if command -v harbor >/dev/null 2>&1 || command -v stb >/dev/null 2>&1; then
  echo "✓ harbor/stb already installed"
elif command -v uv >/dev/null 2>&1; then
  echo "Installing harbor via uv..."
  uv tool install harbor
else
  echo "! uv not found — install harbor manually: uv tool install harbor"
fi

python3 "$ROOT/terminus/scripts/doctor.py" || true

if [ "$CHECK_ONLY" -eq 1 ]; then
  exit 0
fi

echo ""
echo "Quick start:"
echo "  source .venv-review/bin/activate"
echo "  ./scripts/terminus doctor"
echo "  ./scripts/batch-validate.sh"
echo "  ./scripts/oracle-sweep.sh --only ruleforge-victory-book"
echo "  ./scripts/review-fast.sh tasks/<name>"
