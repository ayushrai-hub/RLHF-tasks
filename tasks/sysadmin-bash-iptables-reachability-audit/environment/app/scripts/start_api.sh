#!/bin/bash
set -euo pipefail

API_DIR="/app/api"
LOG_PATH="/tmp/api.log"
PID_PATH="/tmp/api.pid"

if [ -f "$PID_PATH" ] && kill -0 "$(cat "$PID_PATH")" 2>/dev/null; then
    echo "api already running pid=$(cat "$PID_PATH")" >&2
    exit 0
fi

cd "$API_DIR"
nohup python3 -u app.py > "$LOG_PATH" 2>&1 &
echo $! > "$PID_PATH"

for _ in {1..120}; do
    if curl -fsS http://127.0.0.1:8080/health >/dev/null 2>&1; then
        echo "api up pid=$(cat "$PID_PATH")" >&2
        exit 0
    fi
    sleep 0.5
done

echo "api failed to come up" >&2
cat "$LOG_PATH" >&2 || true
exit 1
