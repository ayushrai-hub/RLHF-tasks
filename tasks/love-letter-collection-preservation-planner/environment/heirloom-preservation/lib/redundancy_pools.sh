#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" "$2" <<'PY'
import hashlib, json, sys
data = json.loads(sys.argv[1])
snap_hash = sys.argv[2]
pools = {}
for e in data["artifacts"]:
    pools.setdefault(e["keepsake"], []).append(e["artifact_id"])
for k in pools:
    pools[k] = sorted(pools[k])
pools = dict(sorted(pools.items()))
body = {
    "schema_version": 1,
    "eras": pools,
    "era_count": len(pools),
    "collection_snapshot_hash": snap_hash,
}
body["redundancy_hash"] = hashlib.sha256(
    json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
).hexdigest()
print(json.dumps(body))
PY
