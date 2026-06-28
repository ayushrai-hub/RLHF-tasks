#!/usr/bin/env bash
set -euo pipefail

log() { printf '[solve] %s\n' "$1"; }

cd /app
rm -rf /app/output
mkdir -p /app/output

log "apply ssh bastion reload source fix"
cd /solution
patch -d /app -p0 --batch < oracle.patch

log "run reload driver"
cd /app
node --experimental-strip-types src/reload.ts --input fixtures --output output

log "sanity-check reload artifacts"
python3 <<'PY'
import json
from pathlib import Path

report = json.loads(Path("/app/output/reload_report.json").read_text(encoding="utf-8"))
plan = json.loads(Path("/app/output/policy_plan.json").read_text(encoding="utf-8"))
revoked = json.loads(Path("/app/output/revoke_manifest.json").read_text(encoding="utf-8"))
assert report["summary"]["reload_status"] == "settled"
assert report["summary"]["entries_total"] == len(plan["entries"])
assert report["summary"]["revoked_total"] == len(revoked["revoked"])
assert all(entry["seq"] > 0 for entry in plan["entries"])
PY

log "done"
