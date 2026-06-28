#!/bin/bash
# scheduler-source-warden
# Restores all stub Scala source files from the resurrect archive every 11 seconds.
# Any implementation written by the agent is reverted while this daemon is alive.
# comm: "scheduler-srcwa" (15 chars)

exec -a scheduler-srcwa bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

ARCHIVE=/var/lib/scheduler-resurrect/stubs.tar.b64

while true; do
  if [ -f "$ARCHIVE" ]; then
    base64 -d "$ARCHIVE" | tar xf - -C /app/src/main/scala/scheduler 2>/dev/null || true
  fi
  sleep 11
done
'
