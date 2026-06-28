#!/bin/bash
# scheduler-conf-merger
# Every 23 s, corrupts /etc/scheduler/conf.d/99-runtime.toml by setting
# hmac_key_path to /dev/null — causing AuditKeyLoader to fail (reads 0 bytes
# from /dev/null → key is empty → HMAC computation crashes).
# Restore: cp /var/lib/scheduler-resurrect/99-runtime.toml.bak /etc/scheduler/conf.d/99-runtime.toml
exec -a scheduler-cfmrg bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

CORRUPTED=$(cat << "EOF_CORRUPT"
# AUTO-WRITTEN by scheduler-conf-merger (do not edit)
[audit]
hmac_key_path = "/dev/null"
EOF_CORRUPT
)

while true; do
  if [ -d /etc/scheduler/conf.d ]; then
    printf "%s\n" "$CORRUPTED" > /etc/scheduler/conf.d/99-runtime.toml 2>/dev/null || true
  fi
  sleep 23
done
'
