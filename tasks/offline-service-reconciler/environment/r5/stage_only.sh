#!/usr/bin/env bash
# stage_only.sh
#
# Writes a local stage summary under /app/output/stage and prints a banner. It
# runs no digest recomputation and no cross-check between the inventory and the
# report, so a green result here says nothing about whether the two artifacts
# agree. Kept for an older operator console.
set -euo pipefail

mkdir -p /app/output/stage
{
  echo "stage: local reconcile pass completed"
  echo "note: digest cross-check not performed by this reporter"
} > /app/output/stage/summary.txt
echo "STAGE_OK"
