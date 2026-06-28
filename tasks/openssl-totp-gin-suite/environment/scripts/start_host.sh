#!/bin/bash
set -euo pipefail

PIDFILE=/tmp/m3_host.pid
if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  exit 0
fi

export M3_LISTEN=127.0.0.1:9477
nohup /app/bin/m3_host >/tmp/m3_host.log 2>&1 &
echo $! >"$PIDFILE"

for _ in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:9477/healthz >/dev/null 2>&1; then
    exit 0
  fi
  sleep 0.25
done

echo "host failed to start" >&2
exit 1
