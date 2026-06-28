#!/bin/bash
set -euo pipefail

PIDFILE=/tmp/m3_host.pid
if [[ -f "$PIDFILE" ]]; then
  kill "$(cat "$PIDFILE")" 2>/dev/null || true
  rm -f "$PIDFILE"
fi
