#!/usr/bin/env bash
set -euo pipefail
export Q7_ENV_ROOT="${Q7_ENV_ROOT:-/app/environment}"
SCRATCH="/app/output/scratch"
mkdir -p "$SCRATCH"
DRV_Q7="${Q7_DRV_BIN:-/app/environment/tools/drv_q7/drv_q7}"
for pack in sc_w1 sc_c2 sc_h3 sc_j4; do
  "$DRV_Q7" --pack "$pack" \
    --bundle-out "$SCRATCH/${pack}_bundle.cpio.gz" \
    --ledger-out "$SCRATCH/${pack}_ledger.json" &
done
wait
cp "$SCRATCH/sc_j4_bundle.cpio.gz" /app/output/final_bundle.cpio.gz
cp "$SCRATCH/sc_j4_ledger.json" /app/output/build_ledger.json
