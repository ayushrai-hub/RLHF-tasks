from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

VALID_MODES = {"DIRECT", "HOLD", "REBLEND"}

# Strict (test-time) wrapper applied on top of total_score: a base reduction
# (STRICT_BASE_MULTIPLIER) and a STRICT_MISSED_FLOOR_MULTIPLIER factor for each
# sub-score that falls below its entry in STRICT_FLOORS. cement_conformance_score
# scores the delivered cubic_m-weighted cement content against cement_band;
# weighted_fine_pct is validated against fine_band as a hard quality_floor.
STRICT_BASE_MULTIPLIER = 0.93
STRICT_MISSED_FLOOR_MULTIPLIER = 0.82
STRICT_FLOORS = {
    "coverage_score": 0.92,
    "value_score": 0.87,
    "cement_conformance_score": 0.94,
    "deadline_score": 0.52,
    "throughput_balance_score": 0.90,
    "lane_utilization_score": 0.88,
    "bin_balance_score": 0.92,
}

# Sub-score normalisers and the count/diversity floors (calibrated by measurement).
COVERAGE_DIVISOR = 0.72
VALUE_DIVISOR = 0.74
BIN_BAL_DIVISOR = 0.80
LANE_UTIL_DIVISOR = 0.92
MIN_ASSIGNED = 198
MIN_WINDOWS = 5
MIN_ZONES = 5
MIN_BINS = 5
MIN_MODES = 2
MAX_WINDOW_SHARE = 0.24
MAX_ZONE_SHARE = 0.30
LATE_WINDOW_SHARE = 0.10
MIN_DISTINCT_WATER_VALUES = 10
MIN_WATER_STDDEV = 5.0
CEMENT_GUARD_PAD = 0.30
FINE_GUARD_PAD = 2.5


def _jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _load_num(pour_id):
    return int(str(pour_id).split("-")[-1])


def _load_inputs(input_dir):
    input_dir = Path(input_dir)
    loads = {r["pour_id"]: r for r in _jsonl(input_dir / "pour_orders.jsonl")}
    lines = {r["batch_lane_id"]: r for r in _jsonl(input_dir / "batch_lanes.jsonl")}
    bins = {r["aggregate_bin_id"]: r for r in json.load(open(input_dir / "aggregate_bins.json"))["bins"]}
    windows = {int(r["window"]): r for r in json.load(open(input_dir / "delivery_windows.json"))["windows"]}
    config = json.load(open(input_dir / "mix_config.json"))
    return loads, lines, bins, windows, config


def verify_hashes(input_dir):
    input_dir = Path(input_dir)
    hash_file = input_dir / "input_hashes.json"
    if not hash_file.exists():
        return False, "input_hashes.json missing"
    expected = json.load(open(hash_file))
    for name, want in expected.items():
        path = input_dir.parent / name if name.startswith("scripts/") else input_dir / name
        if not path.exists():
            return False, f"hashed file missing: {name}"
        got = hashlib.sha256(path.read_bytes()).hexdigest()
        if got != want:
            return False, f"hash mismatch for {name}"
    return True, ""


def _read_plan(output_dir):
    output_dir = Path(output_dir)
    plan_path = output_dir / "concrete_dispatch_plan.jsonl"
    if not plan_path.exists():
        raise ValueError("concrete_dispatch_plan.jsonl missing")
    rows = _jsonl(plan_path)
    summary_path = output_dir / "concrete_dispatch_summary.json"
    if not summary_path.exists():
        raise ValueError("concrete_dispatch_summary.json missing")
    return rows, json.load(open(summary_path))


def _value(load, bin):
    return float(load["value"]) * float(bin["priority"])


def _zone_conflict(a, b, seed):
    """Return the deterministic same-window washout-zone conflict state."""
    if a["washout_zone"] != b["washout_zone"]:
        return False
    ai, bi = sorted((_load_num(a["pour_id"]), _load_num(b["pour_id"])))
    digest = hashlib.md5(f"{seed}|{a['washout_zone']}|{ai}|{bi}".encode()).hexdigest()
    band = int(digest[:6], 16) % 100
    same_corridor = a["delivery_route"] == b["delivery_route"]
    return band < (24 if same_corridor else 11)


def _band_score(x, band):
    lo, hi = float(band["low"]), float(band["high"])
    c = (lo + hi) / 2.0
    hw = (hi - lo) / 2.0
    if lo <= x <= hi:
        return max(0.0, min(1.0, 1.0 - 0.15 * (abs(x - c) / hw)))
    d = (lo - x) if x < lo else (x - hi)
    return max(0.0, min(1.0, 0.85 * math.exp(-((d / (1.5 * hw)) ** 2))))


def evaluate(input_dir="/app/task_file/input_data", output_dir="/app/task_file/output_data"):
    loads, lines, bins, windows, config = _load_inputs(input_dir)
    ok, err = verify_hashes(input_dir)
    if not ok:
        return {"total_score": 0.0, "penalty": "input_integrity", "error": err}
    try:
        rows, summary = _read_plan(output_dir)
    except Exception as exc:
        return {"total_score": 0.0, "penalty": "missing_output", "error": str(exc)}

    cement_band = config["cement_band"]
    fine_band = config["fine_band"]
    seed = config["hash_seed"]
    water_bounds_l = config["water_bounds_l"]

    by_load = {}
    priority = []
    lane_slots = Counter()
    lane_volume = Counter()
    window_cubic_m = Counter()
    window_count = Counter()
    zone_count = Counter()
    bin_count = Counter()
    bin_volume = Counter()
    window_loads = defaultdict(list)
    mode_count = Counter()
    waters = []
    delivered_value = 0.0
    delivered_cubic_m = 0.0
    cement_volume = 0.0
    fine_volume = 0.0
    deadline_acc = 0.0

    for row in rows:
        lid = row.get("pour_id")
        if lid not in loads:
            return {"total_score": 0.0, "penalty": "schema", "error": f"unknown pour {lid}"}
        if lid in by_load:
            return {"total_score": 0.0, "penalty": "schema", "error": f"duplicate pour {lid}"}
        if row.get("assigned") is not True:
            return {"total_score": 0.0, "penalty": "schema", "error": f"assigned must be true for {lid}"}
        lineid = row.get("batch_lane_id")
        if lineid not in lines:
            return {"total_score": 0.0, "penalty": "schema", "error": f"unknown lane {lineid}"}
        try:
            window = int(row.get("production_window"))
            temp = float(row.get("batch_water_l"))
            rank = int(row.get("priority_rank"))
        except Exception:
            return {"total_score": 0.0, "penalty": "schema", "error": f"bad numeric field for {lid}"}
        mode = str(row.get("handling_mode", "")).upper()
        if window not in windows:
            return {"total_score": 0.0, "penalty": "schema", "error": f"bad production_window for {lid}"}
        if mode not in VALID_MODES:
            return {"total_score": 0.0, "penalty": "schema", "error": f"bad handling_mode for {lid}"}
        ld = loads[lid]
        ln = lines[lineid]
        bin = bins[ld["aggregate_bin"]]
        if row.get("plant_zone") != ln["plant_zone"]:
            return {"total_score": 0.0, "penalty": "plant_zone", "error": f"{lid} plant_zone must match assigned line"}
        bounds = water_bounds_l[ld["mix_type"]]
        if not (bounds["min"] <= temp <= bounds["max"]):
            return {"total_score": 0.0, "penalty": "temp_range", "error": f"{lid} batch_water_l out of range"}
        if ld["mix_type"] not in ln["mix_types"]:
            return {"total_score": 0.0, "penalty": "lane_mix", "error": f"{lid} mix_type incompatible with {lineid}"}
        if ld["mix_type"] == "PAVING" and not ln["allows_paving"]:
            return {"total_score": 0.0, "penalty": "paving_lane", "error": f"{lid} needs a paving-rated lane"}
        if ld["aggregate_bin"] not in ln["aggregate_bin_groups"]:
            return {"total_score": 0.0, "penalty": "bin_group", "error": f"{lineid} cannot draw {ld['aggregate_bin']}"}
        if window < int(ld["earliest_window"]) or window > int(ld["deadline_window"]):
            return {"total_score": 0.0, "penalty": "pour_window", "error": f"{lid} outside window bounds"}
        if window > int(bin["cutoff_window"]):
            return {"total_score": 0.0, "penalty": "bin_cutoff", "error": f"{lid} after bin cutoff"}
        by_load[lid] = row
        priority.append(rank)
        lane_slots[lineid] += 1
        lane_volume[lineid] += float(ld["cubic_m"])
        window_cubic_m[window] += float(ld["cubic_m"])
        window_count[window] += 1
        zone_count[ln["plant_zone"]] += 1
        bin_count[ld["aggregate_bin"]] += 1
        bin_volume[ld["aggregate_bin"]] += float(ld["cubic_m"])
        window_loads[window].append(ld)
        mode_count[mode] += 1
        waters.append(temp)
        delivered_value += _value(ld, bin)
        delivered_cubic_m += float(ld["cubic_m"])
        cement_volume += float(ld["cement_pct"]) * float(ld["cubic_m"])
        fine_volume += float(ld["fine_pct"]) * float(ld["cubic_m"])
        deadline_acc += (int(ld["deadline_window"]) - window + 1) / max(
            1, int(ld["deadline_window"]) - int(ld["earliest_window"]) + 1
        )

    missing_mandatory = {lid for lid, ld in loads.items() if ld["mandatory"]} - set(by_load)
    if missing_mandatory:
        return {"total_score": 0.0, "penalty": "mandatory_missing", "error": f"missing mandatory {sorted(missing_mandatory)[:5]}"}
    if len(priority) != len(set(priority)) or sorted(priority) != list(range(1, len(priority) + 1)):
        return {"total_score": 0.0, "penalty": "priority", "error": "priority_rank must be permutation 1..N"}
    for lid, row in by_load.items():
        prep = loads[lid].get("requires_admixture_prep", "")
        if prep:
            if prep not in by_load:
                return {"total_score": 0.0, "penalty": "precedence", "error": f"{lid} requires prep pour {prep}"}
            if int(by_load[prep]["production_window"]) > int(row["production_window"]):
                return {"total_score": 0.0, "penalty": "precedence", "error": f"{prep} must precede {lid}"}
    for lineid, count in lane_slots.items():
        ln = lines[lineid]
        if count > int(ln["max_loads"]):
            return {"total_score": 0.0, "penalty": "lane_slots", "error": f"{lineid} slot cap exceeded"}
        if lane_volume[lineid] > float(ln["capacity_cubic_m"]):
            return {"total_score": 0.0, "penalty": "lane_volume", "error": f"{lineid} capacity exceeded"}
    for w, cubicM in window_cubic_m.items():
        if cubicM > float(windows[w]["throughput_capacity_cubic_m"]):
            return {"total_score": 0.0, "penalty": "throughput_capacity", "error": f"window {w} throughput exceeded"}
    for sid, cubicM in bin_volume.items():
        if cubicM > float(bins[sid]["draw_capacity_cubic_m"]):
            return {"total_score": 0.0, "penalty": "bin_capacity", "error": f"bin {sid} draw capacity exceeded"}
    for w, group in window_loads.items():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if _zone_conflict(a, b, seed):
                    return {"total_score": 0.0, "penalty": "zone_conflict", "error": f"conflicting pours share window {w}"}

    def _reachable(ld):
        for ln in lines.values():
            if ld["aggregate_bin"] not in ln["aggregate_bin_groups"]:
                continue
            if ld["mix_type"] not in ln["mix_types"]:
                continue
            if ld["mix_type"] == "PAVING" and not ln["allows_paving"]:
                continue
            return True
        return False

    total_possible = sum(_value(ld, bins[ld["aggregate_bin"]]) for ld in loads.values() if _reachable(ld))
    n = len(by_load)
    cement = cement_volume / delivered_cubic_m if delivered_cubic_m else 0.0
    fine = fine_volume / delivered_cubic_m if delivered_cubic_m else 0.0

    coverage_score = min(1.0, n / len(loads) / COVERAGE_DIVISOR)
    value_score = min(1.0, delivered_value / total_possible / VALUE_DIVISOR) if total_possible else 0.0
    cement_conformance_score = _band_score(cement, cement_band)
    deadline_score = deadline_acc / max(1, n)
    max_window_cubic_m = max(window_cubic_m.values() or [0.0])
    throughput_balance_score = 1.0 - (max_window_cubic_m / max(1.0, delivered_cubic_m) - 1.0 / 6.0) / 0.36
    throughput_balance_score = max(0.0, min(1.0, throughput_balance_score))
    util_terms = [min(1.0, lane_volume[t] / max(1.0, float(lines[t]["capacity_cubic_m"])) / LANE_UTIL_DIVISOR)
                  for t in lane_slots]
    lane_utilization_score = sum(util_terms) / max(1, len(util_terms))
    # Bin balance: reward spreading selected pours evenly across all bins. Each
    # bin at/above its even share saturates to 1.0; under-used bins drag it down.
    expected_per_bin = n / max(1, len(bins))
    bin_terms = [min(1.0, bin_count.get(s, 0) / max(1.0, expected_per_bin) / BIN_BAL_DIVISOR)
                  for s in bins]
    bin_balance_score = sum(bin_terms) / max(1, len(bin_terms))

    total = (
        0.18 * coverage_score
        + 0.16 * value_score
        + 0.26 * cement_conformance_score
        + 0.10 * deadline_score
        + 0.10 * throughput_balance_score
        + 0.10 * lane_utilization_score
        + 0.10 * bin_balance_score
    )

    actual_windows = Counter(str(int(r["production_window"])) for r in rows)
    actual_zones = Counter(lines[r["batch_lane_id"]]["plant_zone"] for r in rows)
    actual_lanes = Counter(r["batch_lane_id"] for r in rows)
    if summary.get("assigned_count") != len(rows):
        return {"total_score": 0.0, "penalty": "summary", "error": "assigned_count mismatch"}
    if {str(k): int(v) for k, v in summary.get("window_counts", {}).items()} != dict(actual_windows):
        return {"total_score": 0.0, "penalty": "summary", "error": "window_counts mismatch"}
    if {str(k): int(v) for k, v in summary.get("zone_counts", {}).items()} != dict(actual_zones):
        return {"total_score": 0.0, "penalty": "summary", "error": "zone_counts mismatch"}
    if {str(k): int(v) for k, v in summary.get("lane_counts", {}).items()} != dict(actual_lanes):
        return {"total_score": 0.0, "penalty": "summary", "error": "lane_counts mismatch"}
    if abs(float(summary.get("delivered_cubic_m", -1)) - delivered_cubic_m) > 0.5:
        return {"total_score": 0.0, "penalty": "summary", "error": "delivered_cubic_m mismatch"}
    if abs(float(summary.get("weighted_cement_pct", -1)) - cement) > 1e-3:
        return {"total_score": 0.0, "penalty": "summary", "error": "weighted_cement_pct mismatch"}
    if abs(float(summary.get("weighted_fine_pct", -1)) - fine) > 1e-3:
        return {"total_score": 0.0, "penalty": "summary", "error": "weighted_fine_pct mismatch"}

    mean_temp = sum(waters) / max(1, len(waters))
    water_stddev = (sum((x - mean_temp) ** 2 for x in waters) / max(1, len(waters))) ** 0.5 if waters else 0.0
    quality_errors = []
    if n < MIN_ASSIGNED:
        quality_errors.append(f"assigned_count must be at least {MIN_ASSIGNED}")
    if len(window_count) < MIN_WINDOWS:
        quality_errors.append(f"at least {MIN_WINDOWS} production windows must be used")
    if len(zone_count) < MIN_ZONES:
        quality_errors.append(f"at least {MIN_ZONES} plant zones must be used")
    if len(bin_count) < MIN_BINS:
        quality_errors.append(f"at least {MIN_BINS} bins must be used")
    if len(mode_count) < MIN_MODES:
        quality_errors.append(f"at least {MIN_MODES} handling modes must be used")
    if max(window_count.values() or [0]) / max(1, n) > MAX_WINDOW_SHARE:
        quality_errors.append(f"no single window may exceed {int(MAX_WINDOW_SHARE * 100)}% of assignments")
    if max(zone_count.values() or [0]) / max(1, n) > MAX_ZONE_SHARE:
        quality_errors.append(f"no single plant zone may exceed {int(MAX_ZONE_SHARE * 100)}% of assignments")
    if window_count.get(5, 0) / max(1, n) < LATE_WINDOW_SHARE or window_count.get(6, 0) / max(1, n) < LATE_WINDOW_SHARE:
        quality_errors.append("windows 5 and 6 must each contain at least 10% of assignments")
    if not (float(cement_band["low"]) - CEMENT_GUARD_PAD <= cement <= float(cement_band["high"]) + CEMENT_GUARD_PAD):
        quality_errors.append(f"delivered weighted_cement_pct must stay within {float(cement_band['low']) - CEMENT_GUARD_PAD}..{float(cement_band['high']) + CEMENT_GUARD_PAD}")
    if not (float(fine_band["low"]) - FINE_GUARD_PAD <= fine <= float(fine_band["high"]) + FINE_GUARD_PAD):
        quality_errors.append(f"delivered weighted_fine_pct must stay within {float(fine_band['low']) - FINE_GUARD_PAD}..{float(fine_band['high']) + FINE_GUARD_PAD}")
    if len({round(v, 2) for v in waters}) < MIN_DISTINCT_WATER_VALUES:
        quality_errors.append(f"batch_water_l must have at least {MIN_DISTINCT_WATER_VALUES} distinct rounded values")
    if water_stddev < MIN_WATER_STDDEV:
        quality_errors.append(f"batch_water_l population standard deviation must be at least {MIN_WATER_STDDEV}")
    if quality_errors:
        return {
            "total_score": 0.0,
            "total_score_strict": 0.0,
            "penalty": "quality_floor",
            "error": "; ".join(quality_errors),
        }

    result = {
        "total_score": round(total, 6),
        "coverage_score": round(coverage_score, 6),
        "value_score": round(value_score, 6),
        "cement_conformance_score": round(cement_conformance_score, 6),
        "deadline_score": round(deadline_score, 6),
        "throughput_balance_score": round(throughput_balance_score, 6),
        "lane_utilization_score": round(lane_utilization_score, 6),
        "bin_balance_score": round(bin_balance_score, 6),
        "assigned_count": n,
        "weighted_cement_pct": round(cement, 6),
        "weighted_fine_pct": round(fine, 6),
        "delivered_cubic_m": round(delivered_cubic_m, 6),
        "window_counts": dict(window_count),
        "zone_counts": dict(zone_count),
        "bin_counts": dict(bin_count),
        "water_stddev": round(water_stddev, 6),
        "summary": summary,
    }
    strict = result["total_score"] * STRICT_BASE_MULTIPLIER
    strict_penalties = {}
    for key, floor in STRICT_FLOORS.items():
        if result.get(key, 0.0) < floor:
            strict *= STRICT_MISSED_FLOOR_MULTIPLIER
            strict_penalties[key] = result.get(key, 0.0)
    result["total_score_strict"] = round(strict, 6)
    result["strict_floor_penalties"] = strict_penalties
    result["strict_floor_requirements"] = dict(STRICT_FLOORS)
    return result
