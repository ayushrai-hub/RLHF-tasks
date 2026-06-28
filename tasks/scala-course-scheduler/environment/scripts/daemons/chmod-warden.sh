#!/bin/bash
# scheduler-chmod-warden
# Sets Scala source files read-only (0444) every 13 seconds, blocking the agent
# from writing new implementations while this daemon is alive.
# comm: "scheduler-chmwd" (15 chars)

exec -a scheduler-chmwd bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

while true; do
  find /app/src/main/scala/scheduler -name "*.scala" -exec chmod 0444 {} \; 2>/dev/null || true
  sleep 13
done
'
