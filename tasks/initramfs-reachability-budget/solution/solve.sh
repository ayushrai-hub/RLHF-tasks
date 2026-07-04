#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd /app/environment
patch -p1 <"${ROOT_DIR}/op_a.patch"
patch -p1 <"${ROOT_DIR}/phase_b.patch"
patch -p1 <"${ROOT_DIR}/reconcile_c.patch"
patch -p1 <"${ROOT_DIR}/inc_store.patch"
patch -p1 <"${ROOT_DIR}/engine.patch"

bash scripts/build_q7.sh
mkdir -p /app/output
bash scripts/batch_q7.sh
tools/cpio_chk/cpio_chk --grid-all \
  --bundle-out /app/output/final_bundle.cpio.gz \
  --ledger-out /app/output/build_ledger.json
