#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="${APP_ROOT:-/app}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCHES="${SCRIPT_DIR}/files/lib"
DEST="${APP_ROOT}/heirloom-preservation/lib"

install -d "${DEST}/decoy"
for f in parse_letterfolio.sh redundancy_pools.sh migration_rollup.sh index_ledger.sh preservation_schedule.sh collection_snapshot_write.sh ingest_manifest.sh run_sequence.sh ingest_stage.sh export_stage.sh common.sh; do
  install -m 0755 "${PATCHES}/${f}" "${DEST}/${f}"
done
install -m 0755 "${PATCHES}/decoy/sentimental_merge.sh" "${DEST}/decoy/sentimental_merge.sh"

cd "${APP_ROOT}"
bash /app/scripts/build.sh
mkdir -p /app/output /app/state
