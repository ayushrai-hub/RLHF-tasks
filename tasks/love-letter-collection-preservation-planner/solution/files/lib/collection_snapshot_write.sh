#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" "$2" <<'PY'
import hashlib, json, sys
data = json.loads(sys.argv[1])
out = sys.argv[2]
artifacts = data["artifacts"]
collection = data["collection"]
payload = {
    "artifacts": artifacts,
    "collection": {k: collection[k] for k in sorted(collection) if k != "schema_version"},
}
h = hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()).hexdigest()
body = {
    "schema_version": 1,
    "validated": True,
    "artifacts": artifacts,
    "collection": collection,
    "collection_snapshot_hash": h,
}
open(out, "w").write(json.dumps(body, indent=2) + "\n")
print(h)
PY
