#!/bin/bash
# scheduler-respawn-watchdog
# Detects when policy-corrupter is missing and re-spawns it.
# Also traps SIGTERM so killing only the watchdog is insufficient — the corrupter must
# also be SIGKILLed for the system to remain quiet.

exec -a scheduler-watchdog bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT

CORRUPTER=/opt/scheduler/daemons/policy-corrupter.sh

while true; do
  # If no scheduler-policy process is alive, respawn it.
  if ! pgrep -f scheduler-policy >/dev/null 2>&1; then
    if [ -x "$CORRUPTER" ]; then
      setsid "$CORRUPTER" >/dev/null 2>&1 < /dev/null &
    fi
  fi
  sleep 7
done
'
