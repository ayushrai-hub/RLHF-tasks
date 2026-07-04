#!/bin/bash
set -euo pipefail

REPORT="/app/workbook/reports/diffusion_report.md"
CHECKSUM_FILE="/app/workbook/out/summary.checksum"

if [[ ! -f "$CHECKSUM_FILE" ]]; then
  echo "missing summary checksum at $CHECKSUM_FILE" >&2
  exit 1
fi

EXPECTED="$(grep -E '^checksum:' "$REPORT" | awk '{print $2}')"
ACTUAL="$(tr -d '[:space:]' < "$CHECKSUM_FILE")"

if [[ -z "$EXPECTED" ]]; then
  echo "report checksum line missing" >&2
  exit 1
fi

if [[ "$EXPECTED" != "$ACTUAL" ]]; then
  echo "checksum mismatch: report=$EXPECTED file=$ACTUAL" >&2
  exit 1
fi

echo "checksum ok: $ACTUAL"
