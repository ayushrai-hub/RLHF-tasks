#!/bin/bash
set -uo pipefail
mkdir -p /app/data /app/logs /app/run /app/output
bash /app/scripts/stop_service.sh 2>/dev/null || true
bash /app/db/init_db.sh > /app/logs/init_db.log 2>&1
export BIND_PORT="${BIND_PORT:-8080}"
export CALENDAR_DB="${CALENDAR_DB:-/app/data/calendar.db}"
nohup tclsh8.6 /app/src/calendar_server.tcl > /app/logs/service.log 2>&1 &
echo $! > /app/run/server.pid
bash /app/scripts/wait_ready.sh
