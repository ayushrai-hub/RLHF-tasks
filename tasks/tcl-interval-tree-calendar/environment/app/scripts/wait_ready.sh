#!/bin/bash
set -uo pipefail
PORT="${BIND_PORT:-8080}"
for i in $(seq 1 60); do
    if curl -fsS --max-time 1 "http://127.0.0.1:${PORT}/healthz" >/dev/null 2>&1; then
        echo "service ready on :${PORT}"
        exit 0
    fi
    sleep 0.5
done
echo "service did not become ready in 30s" >&2
tail -n 80 /app/logs/service.log 2>/dev/null >&2 || true
exit 1
