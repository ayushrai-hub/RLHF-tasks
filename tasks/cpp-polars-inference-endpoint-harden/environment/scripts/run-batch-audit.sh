#!/usr/bin/env bash
set -euo pipefail
bash /app/environment/ci/start-score-server.sh
python3 - <<'PY'
import json
from pathlib import Path
import requests

payload = json.loads(Path("/app/environment/seed/bundled_rows.json").read_text())
resp = requests.post("http://127.0.0.1:19091/v1/batch-score", json=payload, timeout=60)
resp.raise_for_status()
body = resp.json()
Path("/app/output/batch_audit.json").write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")
print("wrote batch_audit", body.get("accepted"), body.get("rejected"))
PY
