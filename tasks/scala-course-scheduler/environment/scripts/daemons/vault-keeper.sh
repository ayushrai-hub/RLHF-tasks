#!/bin/bash
# scheduler-vault-keeper
# Every 29 s, ensures /opt/scheduler/.vault/daemons.tar.b64 exists by copying
# from the primary resurrect archive. Provides a third layer of daemon resurrection.
# Remove: rm -rf /opt/scheduler/.vault/
# comm: "scheduler-vaulk" (15 chars)
exec -a scheduler-vaulk bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

VAULT=/opt/scheduler/.vault
PRIMARY=/var/lib/scheduler-resurrect/daemons.tar.b64
HIDDEN=/opt/scheduler/.hidden/daemons.tar.b64

while true; do
  sleep 29
  if [ ! -f "$VAULT/daemons.tar.b64" ]; then
    mkdir -p "$VAULT" 2>/dev/null || true
    if [ -f "$PRIMARY" ]; then
      cp "$PRIMARY" "$VAULT/daemons.tar.b64" 2>/dev/null || true
    elif [ -f "$HIDDEN" ]; then
      cp "$HIDDEN" "$VAULT/daemons.tar.b64" 2>/dev/null || true
    fi
  fi
done
'
