#!/bin/bash
set -euo pipefail

export PATH="/usr/local/cargo/bin:$PATH"

APP_DIR="${APP_DIR:-/app}"
SOLUTION_DIR="${SOLUTION_DIR:-}"

if [ -z "$SOLUTION_DIR" ] || [ ! -s "$SOLUTION_DIR/main.rs" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  for candidate in     "/solution/src"     "/oracle/src"     "$SCRIPT_DIR/src"     "/app/solution/src"; do
    if [ -s "$candidate/main.rs" ]; then
      SOLUTION_DIR="$candidate"
      break
    fi
  done
fi

if [ -z "$SOLUTION_DIR" ] || [ ! -s "$SOLUTION_DIR/main.rs" ]; then
  echo "solution source not found" >&2
  exit 1
fi

cp "$SOLUTION_DIR/main.rs" "$APP_DIR/src/main.rs"
cd "$APP_DIR"
cargo build --offline --locked --quiet
cargo run --offline --quiet --locked -- --fixtures "$APP_DIR/fixtures" --out "$APP_DIR/out"
