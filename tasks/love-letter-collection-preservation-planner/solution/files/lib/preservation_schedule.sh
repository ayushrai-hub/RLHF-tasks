#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" <<'PY'
import hashlib, json, sys
data = json.loads(sys.argv[1])
artifacts = data["artifacts"]
collection = data["collection"]

def priority_score(e):
    return e["redundancy"] - len(e["crossref"]) - abs(e["media_slot"]) / 12.0

priority_queue = [
    e["artifact_id"]
    for e in sorted(artifacts, key=lambda e: (-priority_score(e), e["artifact_id"]))
]
by_id = {e["artifact_id"]: e for e in artifacts}
n = len(priority_queue)
migration_pairs = []
for i in range(n // 2):
    a, b = priority_queue[i], priority_queue[n - 1 - i]
    if b in by_id[a].get("fragile_with", []) or a in by_id[b].get("fragile_with", []):
        raise SystemExit(f"conflict pairing {a} vs {b}")
    migration_pairs.append(
        {"migration_id": f"r1-m{i + 1}", "primary": a, "replica": b, "round": 1}
    )
band_months = int(collection["block_span_months"])
waves_map = {}
for p in migration_pairs:
    slot_max = max(
        abs(by_id[p["primary"]]["media_slot"]),
        abs(by_id[p["replica"]]["media_slot"]),
    )
    band = slot_max // band_months if band_months > 0 else 0
    waves_map.setdefault(band, []).append(p["migration_id"])
waves = [
    {"wave_epoch": b, "migration_ids": sorted(waves_map[b])} for b in sorted(waves_map)
]
counts = {}
for p in migration_pairs:
    for role in ("primary", "replica"):
        counts[p[role]] = counts.get(p[role], 0) + 1
within_parallel = True
for art, c in counts.items():
    cap = min(by_id[art]["redundancy"], int(collection["max_parallel_migrations"]))
    if c > cap:
        within_parallel = False
storage_used = sum(by_id[p["primary"]]["bytes"] + by_id[p["replica"]]["bytes"] for p in migration_pairs)
within_budget = storage_used <= int(collection.get("storage_byte_budget", storage_used))
body = {
    "schema_version": 1,
    "priority_queue": priority_queue,
    "migration_pairs": migration_pairs,
    "preservation_waves": waves,
    "within_storage_budget": within_parallel and within_budget,
}
body["schedule_hash"] = hashlib.sha256(
    json.dumps({k: body[k] for k in body if k != "schedule_hash"}, separators=(",", ":"), sort_keys=True).encode()
).hexdigest()
print(json.dumps(body))
PY
