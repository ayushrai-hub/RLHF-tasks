#!/usr/bin/env bash
set -euo pipefail
cd /app
/app/bin/geosynth discovery-run
python3 <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path("/app/output/geosynth-discovery-report.json").read_text())
staging = json.loads(Path("/app/state/formation-compose-staging.json").read_text())
bind = json.loads(Path("/app/state/discovery-export-bind.json").read_text())
if bind.get("status") != "finalized":
    sys.exit(2)
if bind.get("discovery_fingerprint") != report.get("discovery_fingerprint"):
    sys.exit(3)
if bind.get("formation_compose_digest") != staging.get("formation_compose_digest"):
    sys.exit(4)
Path("/app/state/discovery-atlas.ok").write_text("ok\n")
PY
