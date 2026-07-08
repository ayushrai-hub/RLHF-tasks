#!/usr/bin/env bash
set -euo pipefail
cd /app/task_file

SOLUTION_DIR="$(dirname "$0")"
patch -p0 < "$SOLUTION_DIR/patches/calibrate.patch"
patch -p0 < "$SOLUTION_DIR/patches/main.patch"

export CARGO_NET_OFFLINE=true
cargo build --release --locked 1>&2
