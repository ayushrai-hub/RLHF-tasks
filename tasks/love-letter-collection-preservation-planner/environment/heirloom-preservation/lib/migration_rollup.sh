#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" "$2" <<'PY'
import hashlib, json, sys
data = json.loads(sys.argv[1])
snap_hash = sys.argv[2]
rollup = {}
for e in data["artifacts"]:
    rollup.setdefault(e["keepsake"], []).append(e["artifact_id"])
for k in rollup:
    rollup[k] = sorted(rollup[k])
rollup = dict(sorted(rollup.items()))
body = {
    "schema_version": 1,
    "format_groups": rollup,
    "format_count": len(rollup),
    "collection_snapshot_hash": snap_hash,
}
body["rollup_hash"] = hashlib.sha256(
    json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
).hexdigest()
print(json.dumps(body))
PY
