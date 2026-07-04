#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi
self="${BASH_SOURCE[0]:-$0}"
self="${self//$'\r'/}"
if grep -q $'\r' "$self" 2>/dev/null; then
  tmp="${TMPDIR:-/tmp}/solve-$$.sh"
  tr -d '\r' < "$self" > "$tmp"
  chmod +x "$tmp"
  exec bash "$tmp" "$@"
fi
set -euo pipefail

export PATH="/usr/local/cargo/bin:/opt/verifier-venv/bin:${PATH}"
export RUSTUP_HOME="${RUSTUP_HOME:-/usr/local/rustup}"
export CARGO_HOME="${CARGO_HOME:-/usr/local/cargo}"
export CARGO_INCREMENTAL=0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC=""
for candidate in \
  "${SCRIPT_DIR}/files" \
  "/solution/files" \
  "/oracle/solution/files" \
  "/task/solution/files"; do
  if [ -f "${candidate}/decode.rs" ]; then
    SRC="${candidate}"
    break
  fi
done

if [ -z "${SRC}" ]; then
  echo "oracle: solution files not found" >&2
  exit 1
fi

cd /app
cp "${SRC}/decode.rs" src/decode.rs
cp "${SRC}/staging_manifest.rs" src/staging_manifest.rs
cp "${SRC}/stage.rs" src/stage.rs
cp "${SRC}/persist.rs" src/persist.rs
cp "${SRC}/ledger.rs" src/ledger.rs
cp "${SRC}/seal.rs" src/seal.rs
cp "${SRC}/export.rs" src/export.rs

/app/scripts/verifier-rebuild.sh
test -x /app/bin/rtcmctl
echo "Oracle solution complete"
