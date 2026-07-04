#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" "$2" <<'PY'
import hashlib, json, sys
data = json.loads(sys.argv[1])
salt = sys.argv[2]
edges = []
for e in data["artifacts"]:
    for h in e["crossref"]:
        edges.append("|".join(sorted([e["artifact_id"], h])))
edges = sorted(set(edges))
digest = hashlib.sha256((salt + "\n" + "\n".join(edges)).encode()).hexdigest()
print(json.dumps({"schema_version": 1, "index_edges": edges, "index_digest": digest}))
PY
