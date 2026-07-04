#!/bin/bash
set -euo pipefail
if curl -sf "http://127.0.0.1:8966/health" >/dev/null 2>&1; then
  exit 0
fi
nohup ruby /workspace/stampgate-api/app.rb >/tmp/stampgate-api.log 2>&1 &
for _ in $(seq 1 30); do
  if curl -sf "http://127.0.0.1:8966/health" >/dev/null 2>&1; then
    exit 0
  fi
  sleep 0.2
done
echo "stampgate api failed to start" >&2
exit 1
