#!/bin/bash
# scheduler-token-refresher
# Every 27 s, regenerates /etc/scheduler/audit.key with fresh random bytes AND
# updates the backup at /var/lib/scheduler-resurrect/audit.key.bak to match.
# Effect: the kill-guard token (hex of first 4 bytes) changes, invalidating any
# comm the agent set earlier.  Kill this daemon AND key-rotator BEFORE reading
# the token, then restore key from backup.
# comm: "scheduler-trefr" (15 chars)
exec -a scheduler-trefr bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2
while true; do
  sleep 27
  dd if=/dev/urandom bs=32 count=1 of=/etc/scheduler/audit.key 2>/dev/null || true
  cp /etc/scheduler/audit.key /var/lib/scheduler-resurrect/audit.key.bak 2>/dev/null || true
done
'
