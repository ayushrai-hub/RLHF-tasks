#!/bin/bash
# scheduler-conf-poisoner
# Every 17 s, hides /etc/scheduler/conf.d/50-overrides.toml as a dot-file.
# This drops the tier count to 9 (test_policy_d_has_ten_tiers fails) and
# removes the demand overlay CSV path from the effective policy.
# Restore: mv /etc/scheduler/conf.d/.50-overrides.toml.save /etc/scheduler/conf.d/50-overrides.toml
# comm: "scheduler-cfpoi" (15 chars)
exec -a scheduler-cfpoi bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2
while true; do
  if [ -f /etc/scheduler/conf.d/50-overrides.toml ]; then
    mv /etc/scheduler/conf.d/50-overrides.toml \
       /etc/scheduler/conf.d/.50-overrides.toml.save 2>/dev/null || true
  fi
  sleep 17
done
'
