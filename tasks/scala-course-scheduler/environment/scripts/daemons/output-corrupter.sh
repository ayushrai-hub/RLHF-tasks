#!/bin/bash
# scheduler-output-corrupter
# Overwrites schedule.json with an empty placeholder every 14 seconds.
# Forces the agent to generate a fresh schedule after all daemons are dead.
# comm: "scheduler-outco" (15 chars)

exec -a scheduler-outco bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

while true; do
  if [ -f /opt/scheduler/schedule.json ]; then
    printf "{}" > /opt/scheduler/schedule.json 2>/dev/null || true
  fi
  sleep 14
done
'
