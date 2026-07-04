#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" <<'PY'
import hashlib, json, sys
data = json.loads(sys.argv[1])
artifacts = data["artifacts"]
collection = data["collection"]
priority_queue = sorted([e["artifact_id"] for e in artifacts])
by_id = {e["artifact_id"]: e for e in artifacts}
n = len(priority_queue)
migration_pairs = []
for i in range(n // 2):
    a, b = priority_queue[i], priority_queue[n - 1 - i]
    migration_pairs.append(
        {"migration_id": f"r1-m{i + 1}", "primary": a, "replica": b, "round": 1}
    )
waves = [{"wave_epoch": 0, "migration_ids": [p["migration_id"] for p in migration_pairs]}]
body = {
    "schema_version": 1,
    "priority_queue": priority_queue,
    "migration_pairs": migration_pairs,
    "preservation_waves": waves,
    "within_storage_budget": True,
}
body["schedule_hash"] = hashlib.sha256(
    json.dumps(body, separators=(",", ":"), sort_keys=True).encode()
).hexdigest()
print(json.dumps(body))
PY
