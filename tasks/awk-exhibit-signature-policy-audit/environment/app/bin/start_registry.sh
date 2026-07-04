#!/bin/bash
# Start the local Trust Registry endpoint in the background and wait until it
# answers. Safe to call more than once: returns immediately if already up.
set -euo pipefail

PORT="${REGISTRY_PORT:-7681}"
BASE="http://127.0.0.1:${PORT}"

if curl -fsS "${BASE}/v1/ping" >/dev/null 2>&1; then
    exit 0
fi

nohup python3 /app/bin/trust_registry.py >/tmp/trust_registry.log 2>&1 &

for _ in $(seq 1 50); do
    if curl -fsS "${BASE}/v1/ping" >/dev/null 2>&1; then
        exit 0
    fi
    sleep 0.2
done

echo "trust registry failed to start" >&2
exit 1
