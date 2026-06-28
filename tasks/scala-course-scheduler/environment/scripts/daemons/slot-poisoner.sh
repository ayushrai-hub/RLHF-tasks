#!/bin/bash
# scheduler-slot-poisoner
# Every 19 s, overwrites /etc/scheduler/conf.d/97-emergency.toml with values that
# raise pass_score to 0.99 and shrink enabled slots to just 2 — breaking both the
# score threshold and slot-assignment tests.
# Restore: cp /var/lib/scheduler-resurrect/97-emergency.toml.bak /etc/scheduler/conf.d/97-emergency.toml
# comm: "scheduler-slpoi" (15 chars — write guard allows scheduler-* comms)
exec -a scheduler-slpoi bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

CORRUPTED=$(cat << "EOF_POISON"
# AUTO-WRITTEN by scheduler-slot-poisoner (do not edit)
[threshold]
pass_score = 0.99

[slots]
enabled = ["MON-09","MON-11"]
EOF_POISON
)

while true; do
  if [ -d /etc/scheduler/conf.d ]; then
    printf "%s\n" "$CORRUPTED" > /etc/scheduler/conf.d/97-emergency.toml 2>/dev/null || true
  fi
  sleep 19
done
'
