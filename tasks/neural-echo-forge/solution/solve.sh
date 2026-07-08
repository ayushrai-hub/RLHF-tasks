#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="${APP_ROOT:-/app}"

SOL_DIR="${SCRIPT_DIR}"
if [[ ! -f "${SOL_DIR}/pipeline.rs" ]]; then
  for try in /oracle /solution /task/solution; do
    if [[ -f "${try}/pipeline.rs" ]]; then
      SOL_DIR="${try}"
      break
    fi
  done
fi

if [[ ! -f "${SOL_DIR}/pipeline.rs" ]]; then
  echo "ERROR: oracle helper sources not found beside ${SCRIPT_DIR}" >&2
  exit 1
fi

cp "${SOL_DIR}/pipeline.rs" "${APP_ROOT}/src/ingest/pipeline.rs"
cp "${SOL_DIR}/publish.rs" "${APP_ROOT}/src/export/publish.rs"
cp "${SOL_DIR}/index_builder.rs" "${APP_ROOT}/src/export/index_builder.rs"
cp "${SOL_DIR}/reconcile.rs" "${APP_ROOT}/src/staging/reconcile.rs"
cp "${SOL_DIR}/staging_ledger.rs" "${APP_ROOT}/src/staging/staging_ledger.rs"
cp "${SOL_DIR}/load.rs" "${APP_ROOT}/src/ingest/load.rs"

cd "${APP_ROOT}"
export PATH="/usr/local/cargo/bin:${PATH}"
export CARGO_HOME=/usr/local/cargo
export RUSTUP_HOME=/usr/local/rustup
export CARGO_INCREMENTAL=0
cargo build --release --locked
cp target/release/neural-echo-forge "${APP_ROOT}/neural-echo-forge"
