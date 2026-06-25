#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

for required in \
  /app/Cargo.toml \
  /app/data/seed/scenarios.json \
  /app/g1/dispatch.rs \
  /app/g2/churn_m.rs \
  /app/g3/voice_m.rs \
  /app/src/ring/audit.rs \
  /app/src/ring/coalesce.rs \
  /app/src/ring/version.rs \
  /app/src/session/ph3.rs \
  /app/src/session/ph6a.rs
do
  if test ! -f "$required"; then
    echo "required file missing: $required" >&2
    exit 1
  fi
done

if test ! -f oracle.patch; then
  echo "oracle.patch missing next to solve.sh" >&2
  exit 1
fi

patch -p1 --no-backup-if-mismatch -d /app < oracle.patch
export PATH="/usr/local/cargo/bin:${PATH}"
cd /app
cargo build --release --locked --offline
./target/release/tracefold

