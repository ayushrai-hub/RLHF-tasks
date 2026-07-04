#!/bin/sh
# Oracle for milestone 1: install the snapshot engine at /app/viewport.py. The
# single program implements all four milestones, so this is self-contained and
# idempotent and works even if an earlier milestone's artifact is absent.
set -eu
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
mkdir -p /app
cp "$SCRIPT_DIR/viewport.py" /app/viewport.py
