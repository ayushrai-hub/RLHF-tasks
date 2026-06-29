#!/bin/bash
# scheduler-binary-corrupter
# Truncates the scheduler JAR and the sbt target copy every 8 seconds.
# Ensures the agent cannot rely on a cached pre-built JAR from before daemon neutralisation.
# comm: "scheduler-binco" (15 chars, fits /proc/comm limit)

exec -a scheduler-binco bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

while true; do
  : > /opt/scheduler/scheduler.jar 2>/dev/null || true
  : > /app/target/scala-3.3.4/scheduler.jar 2>/dev/null || true
  sleep 8
done
'
