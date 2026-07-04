#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="${APP_ROOT:-/app}"
source "${APP_ROOT}/heirloom-preservation/lib/common.sh"
archive_root="/app/heirloom-archive"
if [[ $# -ge 1 && -n "${1:-}" ]]; then archive_root="$1"; fi
if [[ -n "${HEIRLOOM_ARCHIVE_ROOT:-}" ]]; then archive_root="${HEIRLOOM_ARCHIVE_ROOT}"; fi
if [[ ! "$archive_root" = /* ]]; then echo "archive root must be absolute" >&2; exit 1; fi
ensure_dirs
parsed="$(bash "${APP_ROOT}/heirloom-preservation/lib/parse_letterfolio.sh" "${archive_root}/letterfolio" "${archive_root}/collection.json")"
snap_hash="$(bash "${APP_ROOT}/heirloom-preservation/lib/collection_snapshot_write.sh" "$parsed" "${COLLECTION_SNAPSHOT}")"
pool_json="$(bash "${APP_ROOT}/heirloom-preservation/lib/redundancy_pools.sh" "$parsed" "$snap_hash")"
echo "$pool_json" > "${REDUNDANCY_POOLS}"
redundancy_hash="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["redundancy_hash"])' "${REDUNDANCY_POOLS}")"
rollup_json="$(bash "${APP_ROOT}/heirloom-preservation/lib/migration_rollup.sh" "$parsed" "$snap_hash")"
echo "$rollup_json" > "${MIGRATION_ROLLUP}"
rollup_hash="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["rollup_hash"])' "${MIGRATION_ROLLUP}")"
salt="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1]); print(d["collection"]["migration_salt"])' "$parsed")"
ledger_json="$(bash "${APP_ROOT}/heirloom-preservation/lib/index_ledger.sh" "$parsed" "$salt")"
echo "$ledger_json" > "${INDEX_LEDGER}"
index_digest="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["index_digest"])' "${INDEX_LEDGER}")"
schedule_json="$(bash "${APP_ROOT}/heirloom-preservation/lib/preservation_schedule.sh" "$parsed")"
echo "$schedule_json" > "${PRESERVATION_STAGING}"
schedule_hash="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["schedule_hash"])' "${PRESERVATION_STAGING}")"
run_sequence="$(bash "${APP_ROOT}/heirloom-preservation/lib/run_sequence.sh")"
bash "${APP_ROOT}/heirloom-preservation/lib/ingest_manifest.sh" "$snap_hash" "$redundancy_hash" "$rollup_hash" "$index_digest" "$schedule_hash" "$run_sequence" "${INGEST_MANIFEST}"
