#!/usr/bin/env bash
set -euo pipefail
APP_ROOT="${APP_ROOT:-/app}"
source "${APP_ROOT}/heirloom-preservation/lib/common.sh"
python3 - <<'PY'
import hashlib, json
from pathlib import Path
APP = Path("/app")
atlas = {
    "schema_version": 1,
    "collection_label": "stub",
    "priority_queue": [],
    "migration_pairs": [],
    "preservation_waves": [],
    "schedule_hash": "0" * 64,
    "index_digest": "0" * 64,
}
report = {
    "schema_version": 1,
    "artifact_count": 0,
    "migration_count": 0,
    "wave_count": 0,
    "report_fingerprint": hashlib.sha256(b"stub").hexdigest(),
}
(APP / "output").mkdir(parents=True, exist_ok=True)
(APP / "output/preservation-atlas.json").write_text(json.dumps(atlas, indent=2) + "\n")
(APP / "output/preservation-report.json").write_text(json.dumps(report, indent=2) + "\n")
PY
