#!/bin/bash
# scheduler-inotify-warden
# Watches /etc/scheduler/conf.d/ via inotifywait.  If any file is closed-after-write
# by a process whose comm does NOT start with "scheduler-", the warden immediately
# clobbers 90-final.toml with the corrupted defaults.
# Allows the policy-corrupter to do its job, but punishes ad-hoc edits.

exec -a scheduler-warden bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT

CORRUPTED=$(cat << "EOF_CORRUPT"
# AUTO-WRITTEN by scheduler-inotify-warden (do not edit by hand)
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

# If inotifywait is not installed, fall back to a polling loop on the mtime.
if ! command -v inotifywait >/dev/null 2>&1; then
  last_mtime=""
  while true; do
    if [ -f /etc/scheduler/conf.d/90-final.toml ]; then
      mtime=$(stat -c %Y /etc/scheduler/conf.d/90-final.toml 2>/dev/null || echo "")
      if [ -n "$mtime" ] && [ "$mtime" != "$last_mtime" ]; then
        printf "%s\n" "$CORRUPTED" > /etc/scheduler/conf.d/90-final.toml 2>/dev/null || true
        last_mtime=$(stat -c %Y /etc/scheduler/conf.d/90-final.toml 2>/dev/null || echo "")
      fi
    fi
    sleep 4
  done
else
  while true; do
    inotifywait -q -e close_write,moved_to /etc/scheduler/conf.d/ >/dev/null 2>&1 || sleep 4
    printf "%s\n" "$CORRUPTED" > /etc/scheduler/conf.d/90-final.toml 2>/dev/null || true
  done
fi
'
