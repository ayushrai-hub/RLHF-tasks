"""cdn-pop-coassigner - base scoring model (verifier-only)."""
import json
import os

FNV_OFFSET = 0xcbf29ce484222325
FNV_PRIME = 0x100000001b3
MASK64 = (1 << 64) - 1
NUM_GROUPS = 12


def fnv1a(s: str) -> int:
    h = FNV_OFFSET
    for b in s.encode():
        h ^= b
        h = (h * FNV_PRIME) & MASK64
    return h


def group_of(item_id: str) -> int:
    return fnv1a("group|" + item_id) % NUM_GROUPS


def is_forbidden(a: str, b: str) -> bool:
    if a > b:
        a, b = b, a
    return fnv1a("incompat|" + a + "|" + b) % 1000 < 8


def evaluate(input_dir: str, output_dir: str) -> dict:
    input_dir = str(input_dir)
    output_dir = str(output_dir)
    items = {}
    with open(os.path.join(input_dir, "assets.jsonl")) as f:
        for line in f:
            line = line.strip()
            if line:
                s = json.loads(line)
                items[s["asset_id"]] = s
    with open(os.path.join(input_dir, "pops_config.json")) as f:
        cfg = json.load(f)
    buckets = {b["pop_id"]: b for b in cfg["pops"]}
    valid_ids = set(buckets.keys())
    out_path = os.path.join(output_dir, "assignment.jsonl")
    if not os.path.exists(out_path):
        return {"total_score": 0.0, "penalty": "missing_output", "detail": "assignment.jsonl not found"}
    rows = []
    with open(out_path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    assigned = [r["asset_id"] for r in rows]
    if len(assigned) != len(items):
        return {"total_score": 0.0, "penalty": "wrong_count", "detail": f"Expected {len(items)}, got {len(assigned)}"}
    if len(set(assigned)) != len(items):
        return {"total_score": 0.0, "penalty": "duplicate_items", "detail": "Duplicate asset_id"}
    if [s for s in assigned if s not in items]:
        return {"total_score": 0.0, "penalty": "unknown_ids", "detail": "Unknown asset_id"}
    for r in rows:
        if r["pop_id"] not in valid_ids:
            return {"total_score": 0.0, "penalty": "invalid_bucket", "detail": f"Unknown pop_id: {r['pop_id']}"}
    members = {b: [] for b in valid_ids}
    load_by = {b: 0 for b in valid_ids}
    for r in rows:
        members[r["pop_id"]].append(r["asset_id"])
        load_by[r["pop_id"]] += items[r["asset_id"]]["bytes"]
    for b in valid_ids:
        if load_by[b] > buckets[b]["bytes_capacity"]:
            return {"total_score": 0.0, "penalty": "capacity_overflow", "detail": f"{b} exceeds bytes_capacity"}
    same, totp, forb = 0, 0, 0
    for b in valid_ids:
        mem = members[b]
        L = len(mem)
        totp += L * (L - 1) // 2
        for i in range(L):
            gi = group_of(mem[i])
            for j in range(i + 1, L):
                if gi == group_of(mem[j]):
                    same += 1
                if is_forbidden(mem[i], mem[j]):
                    forb += 1
    affinity_score = same / totp if totp > 0 else 1.0
    loads = list(load_by.values())
    tot = sum(loads)
    balance_score = 1.0 - (max(loads) - min(loads)) / tot if tot > 0 else 0.0
    total_score = 0.70 * affinity_score + 0.30 * balance_score
    if forb > 0:
        total_score *= max(0.20, 0.55 ** min(forb, 5))
    total_score = round(max(0.0, min(1.0, total_score)), 4)
    return {"total_score": total_score, "affinity_score": round(affinity_score, 4),
            "balance_score": round(balance_score, 4), "forbidden_co_located": forb}
