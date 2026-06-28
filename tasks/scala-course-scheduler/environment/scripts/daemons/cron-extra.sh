#!/bin/bash
# scheduler-cron-extra
# Every 21 s, recreates /etc/cron.d/scheduler-extra (3-minute interval resurrection).
# This is a FOURTH cron job that `test_extra_cron_removed` checks.
# Kill this daemon before removing the cron file, then: rm -f /etc/cron.d/scheduler-extra
exec -a scheduler-crext bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

while true; do
  if [ ! -f /etc/cron.d/scheduler-extra ]; then
    echo "*/3 * * * * root /opt/scheduler/daemons/launch-all.sh >/dev/null 2>&1" \
      > /etc/cron.d/scheduler-extra 2>/dev/null || true
    chmod 0644 /etc/cron.d/scheduler-extra 2>/dev/null || true
  fi
  sleep 21
done
'
