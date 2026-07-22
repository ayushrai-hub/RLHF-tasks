#!/usr/bin/env bash
# Fast review pipeline: doctor → validate → audit → review report.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASK="${1:-}"
REPORT="${2:-$ROOT/terminus/reviews/entire-report.txt}"

if [ -z "$TASK" ]; then
  echo "Usage: $0 <task-dir> [entire-report.txt]" >&2
  exit 1
fi

cd "$ROOT"
./scripts/terminus doctor || true
./scripts/terminus validate "$TASK"
./scripts/terminus audit "$TASK" ${REPORT:+--report "$REPORT"}
./scripts/terminus review "$TASK" ${REPORT:+--report "$REPORT"}
echo ""
echo "✓ Review artifacts: $TASK/review-report.md  $TASK/audit-report.md"
