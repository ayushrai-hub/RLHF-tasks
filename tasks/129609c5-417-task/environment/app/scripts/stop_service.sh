#!/bin/bash
set -uo pipefail
PID_FILE="/app/run/server.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null || echo "")
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
        kill -TERM "$PID" 2>/dev/null || true
        for _ in $(seq 1 40); do
            kill -0 "$PID" 2>/dev/null || break
            sleep 0.25
        done
        kill -KILL "$PID" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
fi
pkill -9 -f 'busybox httpd' 2>/dev/null || true
pkill -9 -f 'calendar.tcl' 2>/dev/null || true
pkill -9 -f 'calendar_service.py' 2>/dev/null || true
exit 0
