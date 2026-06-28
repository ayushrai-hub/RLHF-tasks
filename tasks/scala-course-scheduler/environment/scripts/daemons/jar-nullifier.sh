#!/bin/bash
# scheduler-jar-nullifier
# Every 7 s, truncates /opt/scheduler/scheduler.jar to 0 bytes.
# Running `java -jar` on a 0-byte file fails with "invalid or corrupt jarfile".
exec -a scheduler-jarnu bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

while true; do
  truncate -s 0 /opt/scheduler/scheduler.jar 2>/dev/null || true
  sleep 7
done
'
