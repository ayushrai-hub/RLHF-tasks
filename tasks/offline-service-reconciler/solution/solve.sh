#!/usr/bin/env bash
# Oracle for offline-service-reconciler.
#
# The three w7 modules ship implemented but with coupled faults: op_a discards
# the baseline signature check, phase_b takes each host's region from the role's
# winning surface instead of resolving fields independently and never records
# unresolvable aliases as removals, and pack_c hashes the provenance canonical
# with a stray leading separator. These targeted patches repair the source; the
# pipeline then regenerates a correct inventory from the read-only surfaces.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd /app
patch -p1 < "${ROOT_DIR}/g_extract_k.patch"
patch -p1 < "${ROOT_DIR}/g_plan_m.patch"
patch -p1 < "${ROOT_DIR}/g_emit_p.patch"

/app/environment/w7/run_entry.sh
/app/environment/r5/inv_verify --all-hosts \
  --inventory-out /app/output/inventory_out.json \
  --report-out    /app/output/reconcile_report.json
