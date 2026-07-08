#!/usr/bin/env bash
# Show the go.mod and the MVS build list for a pinned module version.
# Requires network access to the module proxy.
set -uo pipefail
BIN=/app/gomvs
MOD="${1:-rsc.io/quote}"
VER="${2:-v1.5.2}"
echo "== gomod =="
"$BIN" gomod "$MOD" "$VER"
echo "== mvs =="
"$BIN" mvs "$MOD" "$VER"
