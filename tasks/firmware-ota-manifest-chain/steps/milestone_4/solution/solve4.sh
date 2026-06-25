#!/bin/bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_DIR="${SCRIPT_DIR}/files/src"

PATCHES=(
  apply.rs
  apply_staging.rs
  apply_validate_seq.rs
  chunk_digest.rs
  chunk_staging.rs
  chunks.rs
  envelope_staging.rs
  journal.rs
  main.rs
  rollback.rs
  rollback_staging.rs
  sig_canon.rs
  signature.rs
)

for f in "${PATCHES[@]}"; do
  cp "${PATCH_DIR}/${f}" "${APP_ROOT}/src/${f}"
done

/app/bin/oracle-build-ota.sh
