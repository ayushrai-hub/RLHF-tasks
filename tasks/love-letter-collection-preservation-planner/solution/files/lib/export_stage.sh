#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="${APP_ROOT:-/app}"
source "${APP_ROOT}/heirloom-preservation/lib/common.sh"
for f in "${COLLECTION_SNAPSHOT}" "${REDUNDANCY_POOLS}" "${MIGRATION_ROLLUP}" "${INDEX_LEDGER}" "${PRESERVATION_STAGING}" "${INGEST_MANIFEST}"; do
  [[ -f "$f" ]] || { echo "missing staging: $f" >&2; exit 1; }
done
python3 - <<'PY'
import hashlib, json
from pathlib import Path
APP = Path("/app")
snap = json.loads((APP / "state/collection-snapshot.json").read_text())
pool = json.loads((APP / "state/redundancy-pools.json").read_text())
rollup = json.loads((APP / "state/migration-rollup.json").read_text())
ledger = json.loads((APP / "state/index-ledger.json").read_text())
staging = json.loads((APP / "state/preservation-staging.json").read_text())
manifest = json.loads((APP / "state/ingest-manifest.json").read_text())
if not snap.get("validated"):
    raise SystemExit("snapshot not validated")
if snap["collection_snapshot_hash"] != pool["collection_snapshot_hash"]:
    raise SystemExit("pool hash mismatch")
if pool["redundancy_hash"] != manifest["redundancy_hash"]:
    raise SystemExit("manifest pool mismatch")
if rollup["rollup_hash"] != manifest["rollup_hash"]:
    raise SystemExit("rollup mismatch")
if ledger["index_digest"] != manifest["index_digest"]:
    raise SystemExit("ledger mismatch")
if staging["schedule_hash"] != manifest["schedule_hash"]:
    raise SystemExit("staging mismatch")
if not staging.get("within_storage_budget"):
    raise SystemExit("storage budget exceeded")
collection = snap["collection"]
atlas = {
    "schema_version": 1,
    "collection_label": collection["collection_label"],
    "priority_queue": staging["priority_queue"],
    "migration_pairs": staging["migration_pairs"],
    "preservation_waves": staging["preservation_waves"],
    "schedule_hash": staging["schedule_hash"],
    "index_digest": ledger["index_digest"],
}
bind = json.dumps(atlas, separators=(",", ":"), sort_keys=True)
report = {
    "schema_version": 1,
    "artifact_count": len(snap["artifacts"]),
    "migration_count": len(staging["migration_pairs"]),
    "wave_count": len(staging["preservation_waves"]),
    "report_fingerprint": hashlib.sha256(bind.encode()).hexdigest(),
}
(APP / "output").mkdir(parents=True, exist_ok=True)
(APP / "output/preservation-atlas.json").write_text(json.dumps(atlas, indent=2) + "\n")
(APP / "output/preservation-report.json").write_text(json.dumps(report, indent=2) + "\n")
PY
