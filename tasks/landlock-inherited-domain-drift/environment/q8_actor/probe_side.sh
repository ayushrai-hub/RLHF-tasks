#!/bin/bash
set -euo pipefail
if [[ "${1:-}" == "note" ]]; then
  echo "probe:${2:-none}" >&2
  exit 0
fi
echo "usage: probe_side.sh note PROFILE" >&2
exit 2
