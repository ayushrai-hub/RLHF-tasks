#!/bin/bash
# scheduler-conf-scrambler
# Every 11 s, overwrites /etc/scheduler/conf.d/10-weights.toml with values that make
# load_balance = 0.90, which causes the weights sum to exceed 1.0 and PolicyLoader to throw.
# Restore: cp /var/lib/scheduler-resurrect/10-weights.toml.bak /etc/scheduler/conf.d/10-weights.toml
exec -a scheduler-confsc bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

CORRUPTED=$(cat << "EOF_CORRUPT"
# AUTO-WRITTEN by scheduler-conf-scrambler (do not edit)
[weights]
room_util       = 0.22
faculty_sat     = 0.33
conflict_avoid  = 0.30
load_balance    = 0.90
EOF_CORRUPT
)

while true; do
  if [ -d /etc/scheduler/conf.d ]; then
    printf "%s\n" "$CORRUPTED" > /etc/scheduler/conf.d/10-weights.toml 2>/dev/null || true
  fi
  sleep 11
done
'
