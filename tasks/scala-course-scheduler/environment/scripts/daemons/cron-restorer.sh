#!/bin/bash
# scheduler-cron-restorer
# Every 20 s, recreates /etc/cron.d/scheduler-resurrect and /etc/cron.d/scheduler-aux
# if the agent has removed them, ensuring daemons continue to be resurrected every 1-2 min.
# Neutralise: kill this daemon FIRST, then remove both cron files.
# comm: "scheduler-cronr" (15 chars)
exec -a scheduler-cronr bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2
CRON1="* * * * * root /opt/scheduler/daemons/launch-all.sh >/dev/null 2>&1"
CRON2="*/2 * * * * root /opt/scheduler/daemons/launch-all.sh >/dev/null 2>&1"
while true; do
  if [ ! -f /etc/cron.d/scheduler-resurrect ]; then
    printf "%s\n" "$CRON1" > /etc/cron.d/scheduler-resurrect 2>/dev/null || true
    chmod 0644 /etc/cron.d/scheduler-resurrect 2>/dev/null || true
  fi
  if [ ! -f /etc/cron.d/scheduler-aux ]; then
    printf "%s\n" "$CRON2" > /etc/cron.d/scheduler-aux 2>/dev/null || true
    chmod 0644 /etc/cron.d/scheduler-aux 2>/dev/null || true
  fi
  sleep 20
done
'
