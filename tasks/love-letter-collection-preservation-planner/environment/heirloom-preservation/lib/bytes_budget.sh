#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" "$2" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
pairs = json.loads(sys.argv[2])
artifacts = {e["artifact_id"]: e for e in data["artifacts"]}
collection = data["collection"]
used = sum(
    artifacts[p["primary"]]["bytes"] + artifacts[p["replica"]]["bytes"] for p in pairs
)
budget = int(collection.get("storage_byte_budget", used))
print(json.dumps({"used_bytes": used, "budget_bytes": budget, "within_budget": used <= budget}))
PY
