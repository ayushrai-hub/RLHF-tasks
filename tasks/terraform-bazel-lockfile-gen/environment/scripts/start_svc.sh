#!/bin/bash
set -euo pipefail
nohup /app/environment/bin/depotd >/tmp/depot.log 2>&1 &
for i in $(seq 1 30); do curl -sf http://127.0.0.1:8787/health && exit 0; sleep 0.2; done
exit 1
