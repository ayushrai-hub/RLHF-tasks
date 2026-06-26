import json
from pathlib import Path


PLAN_FILE = "restoration_plan.json"


def _load_feed_data(input_dir):
    feeders = []
    with open(Path(input_dir) / "feeders.jsonl", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                feeders.append(json.loads(line))
    with open(Path(input_dir) / "config.json", encoding="utf-8") as fh:
        config = json.load(fh)
    return feeders, config


def microgrid_resonance_index(left, right, island_id):
    token_sum = sum(ord(ch) for ch in left["id"] + right["id"] + island_id)
    coupled_load = left["surge"] * right["fault"] + right["surge"] * left["fault"]
    return (token_sum + coupled_load + abs(left["value"] - right["value"])) % 11


def _empty_result(error):
    return {
        "error": error,
        "total_score": 0.0,
        "raw_score": 0,
        "violations": [error],
        "critical_spread_score": 0.0,
        "load_balance_score": 0.0,
        "district_coverage_score": 0.0,
    }


def evaluate(input_dir, output_dir):
    feeders, config = _load_feed_data(input_dir)
    feeders_by_id = {row["id"]: row for row in feeders}
    islands = {row["id"]: row for row in config["islands"]}
    plan_path = Path(output_dir) / PLAN_FILE
    if not plan_path.exists():
        return _empty_result("missing restoration_plan.json")
    try:
        with open(plan_path, encoding="utf-8") as fh:
            plan = json.load(fh)
    except json.JSONDecodeError as exc:
        return _empty_result(f"invalid JSON: {exc}")
    assignments = plan.get("assignments")
    if not isinstance(assignments, list):
        return _empty_result("assignments must be a list")

    seen = set()
    island_feeders = {island_id: [] for island_id in islands}
    violations = []
    for row in assignments:
        if not isinstance(row, dict):
            violations.append("assignment rows must be objects")
            continue
        feeder_id = row.get("feeder_id")
        island_id = row.get("island_id")
        if feeder_id not in feeders_by_id:
            violations.append(f"unknown feeder {feeder_id}")
            continue
        if island_id not in islands:
            violations.append(f"unknown island {island_id}")
            continue
        if feeder_id in seen:
            violations.append(f"duplicate feeder {feeder_id}")
            continue
        seen.add(feeder_id)
        island_feeders[island_id].append(feeders_by_id[feeder_id])

    mandatory = set(config["mandatory_feeders"])
    missing = sorted(mandatory - seen)
    if missing:
        violations.append(f"missing mandatory feeders {missing}")

    district_counts = {name: 0 for name in config["district_floor"]}
    for feeder_id in seen:
        district = feeders_by_id[feeder_id]["district"]
        if district in district_counts:
            district_counts[district] += 1
    for district, floor in config["district_floor"].items():
        if district_counts.get(district, 0) < floor:
            violations.append(f"district floor missed for {district}")

    island_kw = {}
    critical_counts = []
    for island_id, island in islands.items():
        local = island_feeders[island_id]
        kw = sum(row["kw"] for row in local)
        surge = sum(row["surge"] for row in local)
        fault = sum(row["fault"] for row in local)
        resilience = sum(row["resilience"] for row in local)
        island_kw[island_id] = kw
        critical_counts.append(sum(1 for row in local if row["critical"]))
        if kw > island["kw_cap"]:
            violations.append(f"{island_id} exceeds kw cap")
        if surge > island["surge_cap"]:
            violations.append(f"{island_id} exceeds surge cap")
        if fault > island["fault_cap"]:
            violations.append(f"{island_id} exceeds fault cap")
        if resilience < island["min_resilience"]:
            violations.append(f"{island_id} misses resilience floor")
        local_districts = {row["district"] for row in local}
        for district in island["required_districts"]:
            if district not in local_districts:
                violations.append(f"{island_id} misses required district {district}")
        for idx, left in enumerate(local):
            for right in local[idx + 1 :]:
                if microgrid_resonance_index(left, right, island_id) <= config["resonance_limit"]:
                    violations.append(f"resonance conflict {left['id']} {right['id']} on {island_id}")

    raw_score = sum(
        feeders_by_id[feeder_id]["value"] * 10
        + feeders_by_id[feeder_id]["resilience"]
        + (45 if feeders_by_id[feeder_id]["critical"] else 0)
        for feeder_id in seen
    )
    floor_scores = [
        min(1.0, district_counts.get(name, 0) / needed)
        for name, needed in config["district_floor"].items()
    ]
    if island_kw:
        spread = max(island_kw.values()) - min(island_kw.values())
    else:
        spread = config["balance_spread_limit"]
    result = {
        "raw_score": raw_score,
        "assigned_count": len(seen),
        "violations": violations,
        "district_coverage_score": round(sum(floor_scores) / len(floor_scores), 4),
        "critical_spread_score": 1.0 if critical_counts and min(critical_counts) >= 1 else 0.0,
        "load_balance_score": round(max(0.0, 1.0 - spread / config["balance_spread_limit"]), 4),
        "island_kw": island_kw,
    }
    if violations:
        result["total_score"] = 0.0
    else:
        result["total_score"] = round(min(1.0, raw_score / config["score_normalizer"]), 4)
    return result
