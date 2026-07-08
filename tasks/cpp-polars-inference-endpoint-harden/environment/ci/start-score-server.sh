#!/usr/bin/env bash
set -euo pipefail
pkill -f '/app/bin/score-server' 2>/dev/null || true
sleep 0.2
/app/bin/score-server &
for _ in $(seq 1 40); do
  if python3 -c "import socket; s=socket.create_connection(('127.0.0.1',19091),1); s.close()" 2>/dev/null; then
    exit 0
  fi
  sleep 0.25
done
echo "score-server failed to bind 19091" >&2
exit 1
