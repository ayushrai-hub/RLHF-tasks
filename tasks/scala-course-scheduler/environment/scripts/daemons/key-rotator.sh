#!/bin/bash
# scheduler-key-rotator
# Overwrites /etc/scheduler/audit.key with 32 fresh random bytes every 23 s.
# If this daemon is alive when the agent runs the JAR, the chain is built with
# the rotated key but model.py may read a different rotation → HMAC mismatch.
# Restore the original key from /var/lib/scheduler-resurrect/audit.key.bak.
# comm: "scheduler-keyro" (15 chars)
exec -a scheduler-keyro bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2
while true; do
  dd if=/dev/urandom bs=32 count=1 of=/etc/scheduler/audit.key 2>/dev/null || true
  sleep 23
done
'
