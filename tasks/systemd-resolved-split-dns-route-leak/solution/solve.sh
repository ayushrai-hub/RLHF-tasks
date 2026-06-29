#!/usr/bin/env bash
set -euo pipefail

log() { printf '[solve] %s\n' "$1"; }

cd /app
mkdir -p /app/output
rm -f /app/output/route_audit.json

log "apply source fixes"
cd /solution
patch -d /app -p0 --batch < merge_k2.patch
patch -d /app -p0 --batch < evict_p5.patch
patch -d /app -p0 --batch < fold_m1.patch
patch -d /app -p0 --batch < emit_h3.patch

log "rebuild and run checker"
rm -rf /app/environment/var/state /app/environment/var/trace
/app/environment/scripts/build_all.sh
ruby /app/environment/cmd/var_check/main.rb --matrix-full --out /app/output/route_audit.json

log "sanity check report"
python3 <<'PY'
import json
from pathlib import Path

data = json.loads(Path("/app/output/route_audit.json").read_text(encoding="utf-8"))
runs = data["matrix_runs"]
assert len(runs) == 8
for row in runs:
    assert row["internal_leak_count"] == 0
    assert row["band_class"] <= 1
    assert row["cross_path_match"] == 1
    assert len(row["route_fingerprint"]) == 64
PY

log "done"
