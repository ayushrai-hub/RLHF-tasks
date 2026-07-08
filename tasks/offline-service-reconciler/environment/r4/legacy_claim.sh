#!/usr/bin/env bash
# Usage: takes one <file> argument.
#
# Textual reader that prints id/role pairs only. It drops generation and epoch
# tags, so it does not carry enough to choose among several claims for one id.
# The reconciliation pipeline does not call it; it remains for human-readable
# dumps.
set -euo pipefail

f="${1:?usage: legacy_claim.sh <file>}"

while IFS= read -r line; do
  case "$line" in
    *'"id"'*) ;;
    *) continue ;;
  esac
  id="$(printf '%s' "$line" | grep -oE '"id"[[:space:]]*:[[:space:]]*"[^"]*"' | sed -E 's/.*:"([^"]*)"/\1/')"
  role="$(printf '%s' "$line" | grep -oE '"role"[[:space:]]*:[[:space:]]*"[^"]*"' | sed -E 's/.*:"([^"]*)"/\1/')"
  printf '%s\t%s\n' "${id:--}" "${role:--}"
done < "$f"
