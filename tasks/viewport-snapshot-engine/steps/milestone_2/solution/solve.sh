#!/bin/sh
# POSIX sh: harnesses may invoke this with sh/dash, so no bashisms.
set -eu
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
sh "$SCRIPT_DIR/solve2.sh"
