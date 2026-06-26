#!/bin/bash
set -euo pipefail
MARK="${1:-wrapped_p1}"
ROUND="${2:-r1}"
ACTOR="${3:-a_one}"
exec /app/environment/d0/cap_drv replay --round "$ROUND" --actor "$ACTOR" --mark "$MARK" --launch sync
