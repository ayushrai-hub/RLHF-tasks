#!/bin/bash
set -euo pipefail
ROOT="${1:-/app/environment}"
HDR="$ROOT/var/gen/version_slot.h"
OBJ="$ROOT/var/objs/libcore/widget.o"
mkdir -p "$(dirname "$OBJ")"
touch -d "@0" "$HDR" "$OBJ" 2>/dev/null || touch "$HDR" "$OBJ"
TS=$(date +%Y%m%d%H%M.%S)
touch -t "$TS" "$HDR"
touch -t "$TS" "$OBJ"
