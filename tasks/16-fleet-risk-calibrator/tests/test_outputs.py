"""Verifier for the fleet risk calibration and dispatch planning task."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


APP = Path("/app")
MODEL_PATH = APP / "config/model.json"
POLICY_PATH = APP / "config/policy.json"
CALLS_PATH = APP / "data/service_calls.csv"
WINDOWS_PATH = APP / "data/sensor_windows.csv"
HISTORY_PATH = APP / "data/asset_history.csv"
LABELS_PATH = APP / "data/maintenance_labels.csv"
CAPACITY_PATH = APP / "data/site_capacity.csv"
OUT_DIR = APP / "out"
ORIGINAL_INPUT_HASHES = {
    MODEL_PATH: "32b662dcc2296fba43ed93ab6f7e9921558877d179f58c195f52070ec6dabf5e",
    POLICY_PATH: "ca7699a2ee17aa95e359a85bbe5346299cd75a8c8e605c8f6de16929a53d79a1",
    CALLS_PATH: "680e3d7d7556dbcab0dcf9dce2e72798e63f02db1790751efb3859092bc8edfa",
    WINDOWS_PATH: "1b6b73dcff475396800f2d3e8a228ad64f0d0d311d4b51075178ae61162b404e",
    HISTORY_PATH: "38ae468a0c9349f9fb8dc1bb7d297668adc4f89ad384e5ab9ce0f23b76e24b1a",
    LABELS_PATH: "98b649f0d20699bad801dc9f552dd6b8dec143c6574eb83bea259a15ab6369e9",
    CAPACITY_PATH: "53e1928e964401d5b43b1485af0ab9021e38cb5fbb70014dc10d68164ec3fe19",
}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_bundle(
    model_path: Path = MODEL_PATH,
    policy_path: Path = POLICY_PATH,
    calls_path: Path = CALLS_PATH,
    windows_path: Path = WINDOWS_PATH,
    history_path: Path = HISTORY_PATH,
    labels_path: Path = LABELS_PATH,
    capacity_path: Path = CAPACITY_PATH,
) -> tuple[dict, dict, list[dict[str, str]], list[dict[str, str]], list[dict[str, str]], dict[str, int], dict[str, dict[str, int]]]:
    model = json.loads(model_path.read_text())
    policy = json.loads(policy_path.read_text())
    calls = read_csv(calls_path)
    windows = read_csv(windows_path)
    history = read_csv(history_path)
    labels = {row["request_id"]: int(row["failure_within_30d"]) for row in read_csv(labels_path)}
    capacity = {
        row["site"]: {"dispatch_slots": int(row["dispatch_slots"]), "inspect_slots": int(row["inspect_slots"])}
        for row in read_csv(capacity_path)
    }
    return model, policy, calls, windows, history, labels, capacity


def latest_window(call: dict[str, str], windows: list[dict[str, str]]) -> dict[str, str]:
    opened_at = parse_time(call["opened_at"])
    candidates = [
        row
        for row in windows
        if row["asset_id"] == call["asset_id"] and parse_time(row["window_end"]) <= opened_at
    ]
    if not candidates:
        raise AssertionError(f"fixture has no window for {call['request_id']}")
    return max(candidates, key=lambda row: parse_time(row["window_end"]))


def previous_window(window: dict[str, str], windows: list[dict[str, str]]) -> dict[str, str] | None:
    matched_end = parse_time(window["window_end"])
    candidates = [
        row
        for row in windows
        if row["asset_id"] == window["asset_id"] and parse_time(row["window_end"]) < matched_end
    ]
    return max(candidates, key=lambda row: parse_time(row["window_end"])) if candidates else None


def effective_temp(
    window: dict[str, str],
    windows: list[dict[str, str]],
    asset_cfg: dict[str, float],
    params: dict[str, float],
) -> float:
    if window["temp_c"].strip():
        return float(window["temp_c"])
    matched_end = parse_time(window["window_end"])
    numerator = 0.0
    denominator = 0.0
    for candidate in windows:
        if candidate["asset_id"] != window["asset_id"] or not candidate["temp_c"].strip():
            continue
        candidate_end = parse_time(candidate["window_end"])
        if candidate_end >= matched_end:
            continue
        age_hours = (matched_end - candidate_end).total_seconds() / 3600.0
        if age_hours > float(params["trend_lookback_hours"]):
            continue
        weight = 0.5 ** (age_hours / float(params["temp_ewma_half_life_hours"]))
        numerator += float(candidate["temp_c"]) * weight
        denominator += weight
    return float(asset_cfg["impute_temp_c"]) if denominator == 0 else numerator / denominator


def vibration_slope(
    window: dict[str, str],
    windows: list[dict[str, str]],
    asset_cfg: dict[str, float],
    params: dict[str, float],
) -> float:
    matched_end = parse_time(window["window_end"])
    candidates = []
    for candidate in windows:
        if candidate["asset_id"] != window["asset_id"]:
            continue
        candidate_end = parse_time(candidate["window_end"])
        if candidate_end > matched_end:
            continue
        age_hours = (matched_end - candidate_end).total_seconds() / 3600.0
        if age_hours <= float(params["trend_lookback_hours"]):
            candidates.append(candidate)
    if len(candidates) < 2:
        return 0.0
    candidates.sort(key=lambda row: parse_time(row["window_end"]))
    origin = parse_time(candidates[0]["window_end"])
    xs = [(parse_time(row["window_end"]) - origin).total_seconds() / 86400.0 for row in candidates]
    ys = [float(row["vibration_mm_s"]) for row in candidates]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return 0.0
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
    return min(max(0.0, slope / float(asset_cfg["max_vibration_mm_s"])), 1.5)


def feature_vector(
    call: dict[str, str],
    window: dict[str, str],
    windows: list[dict[str, str]],
    history: list[dict[str, str]],
    model: dict,
) -> dict[str, float]:
    asset_cfg = model["asset_types"][call["asset_type"]]
    params = model["feature_params"]
    temp = effective_temp(window, windows, asset_cfg, params)
    prior = previous_window(window, windows)
    prior_temp = effective_temp(prior, windows, asset_cfg, params) if prior else float(asset_cfg["impute_temp_c"])
    opened_at = parse_time(call["opened_at"])
    repeat_repairs = 0
    severity_memory = 0
    history_decay = 0.0
    for event in history:
        if event["asset_id"] != call["asset_id"]:
            continue
        event_time = parse_time(event["event_time"])
        if event_time >= opened_at:
            continue
        age_days = (opened_at - event_time).total_seconds() / 86400.0
        if event["event_type"] == "corrective" and age_days <= 45:
            repeat_repairs += 1
        if event["event_type"] in {"corrective", "failure"} and age_days <= 90:
            severity_memory = max(severity_memory, int(event["severity"]))
        if event["event_type"] in {"corrective", "failure"} and age_days <= float(params["history_lookback_days"]):
            history_decay += (int(event["severity"]) / 5.0) * (0.5 ** (age_days / float(params["history_half_life_days"])))
    pressure_drift = 0.0
    if prior:
        pressure_drift = abs(float(window["pressure_kpa"]) - float(prior["pressure_kpa"])) / float(asset_cfg["nominal_pressure_kpa"])
    return {
        "temp_over_limit": max(0.0, temp - float(asset_cfg["temp_limit_c"])) / 10.0,
        "vibration_ratio": min(float(window["vibration_mm_s"]) / float(asset_cfg["max_vibration_mm_s"]), 3.0),
        "pressure_delta": abs(float(window["pressure_kpa"]) - float(asset_cfg["nominal_pressure_kpa"]))
        / float(asset_cfg["nominal_pressure_kpa"]),
        "current_z": (float(window["current_a"]) - float(asset_cfg["current_mean_a"]))
        / float(asset_cfg["current_std_a"]),
        "runtime_log": math.log1p(float(window["runtime_hours"])) / 10.0,
        "urgent_flag": 1.0 if call["priority"] == "urgent" else 0.0,
        "rework_flag": 1.0 if call["notes_code"] == "REWORK" else 0.0,
        "tech_hours_scaled": float(call["technician_hours"]) / 4.0,
        "temp_rise": max(0.0, temp - prior_temp) / 10.0,
        "repeat_repair_rate": min(repeat_repairs, 3) / 3.0,
        "severity_memory": severity_memory / 5.0,
        "vibration_slope": vibration_slope(window, windows, asset_cfg, params),
        "history_decay": min(history_decay, 2.5) / 2.5,
        "leak_flag": 1.0 if call["notes_code"] == "LEAK" else 0.0,
        "heat_flag": 1.0 if call["notes_code"] == "HEAT" else 0.0,
        "pressure_drift": pressure_drift,
    }


def calibrate(raw: float, knots: list[dict[str, float]]) -> float:
    if raw <= knots[0]["raw"]:
        return knots[0]["calibrated"]
    for left, right in zip(knots, knots[1:]):
        if raw <= right["raw"]:
            span = right["raw"] - left["raw"]
            fraction = (raw - left["raw"]) / span if span else 1.0
            return left["calibrated"] + fraction * (right["calibrated"] - left["calibrated"])
    return knots[-1]["calibrated"]


def calibration_slope(raw: float, knots: list[dict[str, float]]) -> float:
    if len(knots) < 2:
        return 1.0
    if raw < knots[0]["raw"] or raw > knots[-1]["raw"]:
        return 0.0
    for left, right in zip(knots, knots[1:]):
        if raw <= right["raw"]:
            span = right["raw"] - left["raw"]
            return 0.0 if span == 0 else (right["calibrated"] - left["calibrated"]) / span
    return 0.0


def isotonic_predict(raw_score: float, observations: list[dict[str, float]]) -> float | None:
    blocks: list[dict[str, float]] = []
    for observation in sorted(observations, key=lambda row: float(row["raw"])):
        weight = float(observation["weight"])
        if weight <= 0:
            continue
        blocks.append(
            {
                "left": float(observation["raw"]),
                "right": float(observation["raw"]),
                "weight": weight,
                "mean": float(observation["label"]),
            }
        )
        while len(blocks) >= 2 and blocks[-2]["mean"] > blocks[-1]["mean"] + 1e-15:
            last = blocks.pop()
            previous = blocks.pop()
            merged_weight = previous["weight"] + last["weight"]
            blocks.append(
                {
                    "left": previous["left"],
                    "right": last["right"],
                    "weight": merged_weight,
                    "mean": (previous["mean"] * previous["weight"] + last["mean"] * last["weight"]) / merged_weight,
                }
            )
    if not blocks:
        return None
    for block in blocks:
        if raw_score <= block["right"]:
            return min(max(block["mean"], 0.0), 1.0)
    return min(max(blocks[-1]["mean"], 0.0), 1.0)


def post_calibrated_risk(raw_score: float, base_risk: float, model: dict, asset_type: str) -> float:
    post = model.get("post_calibration", {})
    blend_weight = float(post.get("blend_weight", 0.0))
    if blend_weight <= 0:
        return base_risk
    blend_weight = min(blend_weight, 1.0)
    observations = post.get("groups", {}).get(asset_type, [])
    panel_risk = isotonic_predict(raw_score, observations)
    if panel_risk is None:
        return base_risk
    return (1.0 - blend_weight) * base_risk + blend_weight * panel_risk


def top_integrated_factor(features: dict[str, float], model: dict, asset_type: str) -> str:
    steps = 32
    blend = model["blend_by_asset_type"][asset_type]
    feature_names = sorted(features)
    attribution = {name: 0.0 for name in feature_names}
    for step in range(steps):
        alpha = (step + 0.5) / steps
        for head_name in sorted(model["heads"]):
            head = model["heads"][head_name]
            logit = float(head["intercept"])
            for feature_name in feature_names:
                logit += alpha * features[feature_name] * float(head["weights"].get(feature_name, 0.0))
            raw = 1.0 / (1.0 + math.exp(-logit))
            common = (
                float(blend[head_name])
                * calibration_slope(raw, head["calibration"])
                * raw
                * (1.0 - raw)
            )
            for feature_name in feature_names:
                attribution[feature_name] += (
                    features[feature_name]
                    * common
                    * float(head["weights"].get(feature_name, 0.0))
                    / steps
                )
    top_factor = "none"
    top_value = 0.0
    for name in feature_names:
        if attribution[name] > top_value:
            top_value = attribution[name]
            top_factor = name
    return top_factor


def score_call(
    call: dict[str, str],
    window: dict[str, str],
    windows: list[dict[str, str]],
    history: list[dict[str, str]],
    model: dict,
    policy: dict,
) -> dict[str, str | float | int]:
    features = feature_vector(call, window, windows, history, model)
    raw_by_head: dict[str, float] = {}
    calibrated_by_head: dict[str, float] = {}
    blend = model["blend_by_asset_type"][call["asset_type"]]
    for head_name in sorted(model["heads"]):
        head = model["heads"][head_name]
        contributions = {name: features[name] * float(weight) for name, weight in head["weights"].items()}
        logit = float(head["intercept"]) + sum(contributions.values())
        raw = 1.0 / (1.0 + math.exp(-logit))
        raw_by_head[head_name] = raw
        calibrated_by_head[head_name] = calibrate(raw, head["calibration"])
    raw_score = sum(float(weight) * raw_by_head[name] for name, weight in blend.items())
    base_risk = sum(float(weight) * calibrated_by_head[name] for name, weight in blend.items())
    risk = post_calibrated_risk(raw_score, base_risk, model, call["asset_type"])
    thresholds = policy["thresholds"]
    if risk >= thresholds["dispatch"]:
        band = "high"
    elif risk >= thresholds["inspect"]:
        band = "medium"
    elif risk >= thresholds["watch"]:
        band = "watch"
    else:
        band = "low"
    top_factor = top_integrated_factor(features, model, call["asset_type"])
    return {
        "request_id": call["request_id"],
        "asset_id": call["asset_id"],
        "asset_type": call["asset_type"],
        "site": call["site"],
        "opened_at": call["opened_at"],
        "priority": call["priority"],
        "raw_score": raw_score,
        "calibrated_risk": risk,
        "downtime_risk": calibrated_by_head["downtime"],
        "risk_band": band,
        "action": "monitor",
        "top_factor": top_factor,
        "due_within_hours": int(policy["due_hours"]["monitor"]),
        "decision_value": 0.0,
        "reason": f"{top_factor}:{band}",
    }


def action_utility(item: dict[str, str | float | int], action: str, policy: dict) -> float:
    if action == "monitor":
        return 0.0
    optimizer = policy["optimizer"]
    bonus = optimizer["priority_bonus"].get(str(item["priority"]), {}).get(action, 0.0)
    return (
        float(item["calibrated_risk"]) * float(optimizer["risk_effect"][action])
        + float(item["downtime_risk"]) * float(optimizer["downtime_effect"][action])
        + float(bonus)
        - float(optimizer["action_cost"][action])
    )


def feasible_actions(item: dict[str, str | float | int], policy: dict) -> list[str]:
    risk = float(item["calibrated_risk"])
    actions = ["monitor"]
    if risk >= policy["optimizer"]["minimum_risk"]["inspect"] or (
        item["priority"] == "urgent" and risk >= policy["thresholds"]["urgent_inspect_floor"]
    ):
        actions.append("inspect")
    if risk >= policy["optimizer"]["minimum_risk"]["dispatch"]:
        actions.append("dispatch")
    return actions


def action_hours(item: dict[str, str | float | int], action: str, policy: dict) -> float:
    if action == "monitor":
        return 0.0
    return float(policy["optimizer"].get("action_hours", {}).get(action, {}).get(str(item["asset_type"]), 0.0))


def action_parts(item: dict[str, str | float | int], action: str, policy: dict) -> dict[str, int]:
    return {
        str(part_id): int(quantity)
        for part_id, quantity in policy["optimizer"].get("action_parts", {}).get(action, {}).get(str(item["asset_type"]), {}).items()
        if int(quantity) > 0
    }


def evaluate_plan(
    items: list[dict[str, str | float | int]],
    actions: list[str] | tuple[str, ...],
    policy: dict,
) -> tuple[float, float, float, float, str]:
    total = 0.0
    dispatch_risk = 0.0
    inspect_risk = 0.0
    crew_hours = 0.0
    signature = []
    for item, action in zip(items, actions):
        total += action_utility(item, action, policy)
        if action == "dispatch":
            dispatch_risk += float(item["calibrated_risk"])
        if action == "inspect":
            inspect_risk += float(item["calibrated_risk"])
        crew_hours += action_hours(item, action, policy)
        signature.append(f"{item['request_id']}={action}")
    return total, dispatch_risk, inspect_risk, -crew_hours, "|".join(signature)


def schedule_signature(rows: list[dict[str, object]]) -> str:
    ordered = sorted(rows, key=lambda row: str(row["request_id"]))
    return "|".join(f"{row['request_id']}={row['crew_id']}@{format_utc(row['start_at'])}" for row in ordered)


def part_signature(rows: list[dict[str, object]]) -> str:
    return "|".join(
        f"{row['request_id']}:{row['part_id']}={row['source_site']}>{row['dest_site']}@{format_utc(row['ready_at'])}"
        for row in sorted(rows, key=part_sort_key)
    )


def schedule_sort_key(row: dict[str, object]) -> tuple[datetime, str, str]:
    return row["start_at"], str(row["crew_id"]), str(row["request_id"])  # type: ignore[return-value]


def part_sort_key(row: dict[str, object]) -> tuple[str, str, str, str]:
    return str(row["request_id"]), str(row["part_id"]), str(row["source_site"]), str(row["dest_site"])


def build_part_inventory(policy: dict) -> dict[str, dict[str, int]]:
    inventory: dict[str, dict[str, int]] = defaultdict(dict)
    for row in policy["optimizer"].get("parts_inventory", []):
        available = max(0, int(row["on_hand"]) - int(row["reserve_min"]))
        site = str(row["site"])
        part_id = str(row["part_id"])
        inventory[site][part_id] = inventory[site].get(part_id, 0) + available
    return inventory


def part_transfer_hours(policy: dict, region: str, source_site: str, dest_site: str) -> float | None:
    try:
        return float(policy["optimizer"]["part_transfer_hours"][region][source_site][dest_site])
    except KeyError:
        return None


def part_options(
    item: dict[str, str | float | int],
    action: str,
    region: str,
    inventory: dict[str, dict[str, int]],
    policy: dict,
) -> list[tuple[list[dict[str, object]], datetime, float, str]]:
    requirements = action_parts(item, action, policy)
    report_at = parse_time(policy["report_generated_at"])
    if not requirements:
        return [([], report_at, 0.0, "")]
    sites = sorted(site for site in inventory if policy["optimizer"]["site_region"].get(site) == region)
    part_ids = sorted(requirements)
    current: list[dict[str, object]] = []
    options: list[tuple[list[dict[str, object]], datetime, float, str]] = []

    def search(index: int, ready_at: datetime, transfer_total: float) -> None:
        if index == len(part_ids):
            rows = sorted((dict(row) for row in current), key=part_sort_key)
            options.append((rows, ready_at, transfer_total, part_signature(rows)))
            return
        part_id = part_ids[index]
        quantity = requirements[part_id]
        for source_site in sites:
            if inventory[source_site].get(part_id, 0) < quantity:
                continue
            transfer = part_transfer_hours(policy, region, source_site, str(item["site"]))
            if transfer is None:
                continue
            part_ready = report_at + timedelta(hours=transfer)
            inventory[source_site][part_id] -= quantity
            current.append(
                {
                    "request_id": item["request_id"],
                    "part_id": part_id,
                    "source_site": source_site,
                    "dest_site": item["site"],
                    "quantity": quantity,
                    "ready_at": part_ready,
                    "transfer_hours": transfer,
                }
            )
            search(index + 1, max(ready_at, part_ready), transfer_total + transfer * quantity)
            current.pop()
            inventory[source_site][part_id] += quantity

    search(0, report_at, 0.0)
    return sorted(options, key=lambda option: (option[1], option[2], option[3]))


def apply_part_option(inventory: dict[str, dict[str, int]], rows: list[dict[str, object]], delta: int) -> None:
    for row in rows:
        inventory[str(row["source_site"])][str(row["part_id"])] += delta * int(row["quantity"])


def best_schedule(
    items: list[dict[str, str | float | int]],
    actions: list[str] | tuple[str, ...],
    policy: dict,
) -> tuple[list[dict[str, object]], list[dict[str, object]], datetime, float, float] | None:
    report_at = parse_time(policy["report_generated_at"])
    tasks = []
    for item, action in zip(items, actions):
        if action == "monitor":
            continue
        region = policy["optimizer"]["site_region"][str(item["site"])]
        tasks.append(
            {
                "item": item,
                "action": action,
                "region": region,
                "duration": timedelta(hours=action_hours(item, action, policy)),
                "due_by": report_at + timedelta(hours=int(policy["due_hours"][action])),
            }
        )
    if not tasks:
        return [], [], report_at, 0.0, 0.0

    inventory = build_part_inventory(policy)
    crews = []
    for crew in sorted(policy["optimizer"].get("crew_roster", []), key=lambda row: row["crew_id"]):
        shift_start = parse_time(crew["shift_start"])
        max_continuous_hours = float(crew.get("max_continuous_hours", math.inf))
        if max_continuous_hours <= 0:
            max_continuous_hours = math.inf
        crews.append(
            {
                "crew": crew,
                "shift_start": shift_start,
                "shift_end": parse_time(crew["shift_end"]),
                "available": shift_start,
                "site": crew["home_site"],
                "max_continuous_hours": max_continuous_hours,
                "continuous_hours": 0.0,
            }
        )

    best: tuple[list[dict[str, object]], list[dict[str, object]], datetime, float, float, str, str] | None = None
    used = [False] * len(tasks)
    current: list[dict[str, object]] = []
    current_parts: list[dict[str, object]] = []

    def travel_hours(region: str, from_site: str, to_site: str) -> float:
        return float(policy["optimizer"]["travel_hours"][region][from_site][to_site])

    def search(done: int, total_travel: float, total_transfer: float) -> None:
        nonlocal best
        if done == len(tasks):
            rows = sorted((dict(row) for row in current), key=schedule_sort_key)
            part_rows = sorted((dict(row) for row in current_parts), key=part_sort_key)
            max_end = max((row["end_at"] for row in rows), default=report_at)
            signature = schedule_signature(rows)
            parts_sig = part_signature(part_rows)
            candidate = (rows, part_rows, max_end, total_travel, total_transfer, signature, parts_sig)
            if best is None:
                best = candidate
            elif max_end < best[2]:
                best = candidate
            elif max_end == best[2] and total_travel < best[3] - 1e-12:
                best = candidate
            elif max_end == best[2] and abs(total_travel - best[3]) <= 1e-12 and total_transfer < best[4] - 1e-12:
                best = candidate
            elif (
                max_end == best[2]
                and abs(total_travel - best[3]) <= 1e-12
                and abs(total_transfer - best[4]) <= 1e-12
                and signature < best[5]
            ):
                best = candidate
            elif (
                max_end == best[2]
                and abs(total_travel - best[3]) <= 1e-12
                and abs(total_transfer - best[4]) <= 1e-12
                and signature == best[5]
                and parts_sig < best[6]
            ):
                best = candidate
            return
        for task_index, task in enumerate(tasks):
            if used[task_index]:
                continue
            used[task_index] = True
            item = task["item"]
            for crew_state in crews:
                crew = crew_state["crew"]
                if crew["region"] != task["region"]:
                    continue
                task_hours = action_hours(item, str(task["action"]), policy)
                if task_hours > float(crew_state["max_continuous_hours"]) + 1e-12:
                    continue
                available = crew_state["available"]
                continuous_hours = float(crew_state["continuous_hours"])
                if continuous_hours + task_hours > float(crew_state["max_continuous_hours"]) + 1e-12:
                    available = available + timedelta(hours=float(policy["optimizer"].get("break_hours", 0.0)))
                    continuous_hours = 0.0
                travel = travel_hours(str(task["region"]), str(crew_state["site"]), str(item["site"]))
                for part_rows, ready_at, transfer_total, _signature in part_options(
                    item,
                    str(task["action"]),
                    str(task["region"]),
                    inventory,
                    policy,
                ):
                    start_at = max(available + timedelta(hours=travel), ready_at)
                    end_at = start_at + task["duration"]
                    if end_at > crew_state["shift_end"] or end_at > task["due_by"]:
                        continue
                    previous_available = crew_state["available"]
                    previous_site = crew_state["site"]
                    previous_continuous_hours = crew_state["continuous_hours"]
                    apply_part_option(inventory, part_rows, -1)
                    crew_state["available"] = end_at
                    crew_state["site"] = item["site"]
                    crew_state["continuous_hours"] = continuous_hours + task_hours
                    current.append(
                        {
                            "request_id": item["request_id"],
                            "crew_id": crew["crew_id"],
                            "region": task["region"],
                            "site": item["site"],
                            "action": task["action"],
                            "start_at": start_at,
                            "end_at": end_at,
                            "travel_hours": travel,
                        }
                    )
                    current_parts.extend(part_rows)
                    search(done + 1, total_travel + travel, total_transfer + transfer_total)
                    if part_rows:
                        del current_parts[-len(part_rows) :]
                    current.pop()
                    crew_state["available"] = previous_available
                    crew_state["site"] = previous_site
                    crew_state["continuous_hours"] = previous_continuous_hours
                    apply_part_option(inventory, part_rows, 1)
            used[task_index] = False

    search(0, 0.0, 0.0)
    if best is None:
        return None
    return best[0], best[1], best[2], best[3], best[4]


def better_plan(
    candidate: tuple[float, float, float, float, float, float, float, str],
    incumbent: tuple[float, float, float, float, float, float, float, str] | None,
) -> bool:
    if incumbent is None:
        return True
    for candidate_value, incumbent_value in zip(candidate[:7], incumbent[:7]):
        if candidate_value > incumbent_value + 1e-12:
            return True
        if abs(candidate_value - incumbent_value) > 1e-12:
            return False
    return candidate[7] < incumbent[7]


def better_base_key(
    candidate: tuple[float, float, float, float, str],
    incumbent: tuple[float, float, float, float, float, float, float, str],
) -> bool:
    for candidate_value, incumbent_value in zip(candidate[:4], incumbent[:4]):
        if candidate_value > incumbent_value + 1e-12:
            return True
        if abs(candidate_value - incumbent_value) > 1e-12:
            return False
    return True


def optimize_actions(
    items: list[dict[str, str | float | int]],
    policy: dict,
    capacity: dict[str, dict[str, int]],
) -> list[dict[str, object]]:
    ordered = sorted(items, key=lambda item: str(item["request_id"]))
    site_usage: defaultdict[str, dict[str, float]] = defaultdict(lambda: {"dispatch": 0.0, "inspect": 0.0})
    region_usage: defaultdict[str, dict[str, float]] = defaultdict(
        lambda: {"dispatch": 0.0, "inspect": 0.0, "crew_hours": 0.0}
    )
    actions: list[str] = []
    best_actions: list[str] | None = None
    best_schedule_rows: list[dict[str, object]] | None = None
    best_part_rows: list[dict[str, object]] | None = None
    best_key: tuple[float, float, float, float, float, float, float, str] | None = None

    def fits(item: dict[str, str | float | int], action: str) -> bool:
        site = str(item["site"])
        next_site_dispatch = site_usage[site]["dispatch"] + (1.0 if action == "dispatch" else 0.0)
        next_site_inspect = site_usage[site]["inspect"] + (1.0 if action == "inspect" else 0.0)
        if next_site_dispatch > capacity[site]["dispatch_slots"]:
            return False
        if next_site_inspect > capacity[site]["inspect_slots"]:
            return False
        if action == "monitor":
            return True
        region = policy["optimizer"]["site_region"][site]
        limit = policy["optimizer"]["regional_limits"][region]
        hours = action_hours(item, action, policy)
        next_region_dispatch = region_usage[region]["dispatch"] + (1.0 if action == "dispatch" else 0.0)
        next_region_inspect = region_usage[region]["inspect"] + (1.0 if action == "inspect" else 0.0)
        next_region_hours = region_usage[region]["crew_hours"] + hours
        return (
            next_region_dispatch <= float(limit["dispatch_slots"])
            and next_region_inspect <= float(limit["inspect_slots"])
            and next_region_hours <= float(limit["crew_hours"]) + 1e-12
        )

    def apply(item: dict[str, str | float | int], action: str, delta: float) -> None:
        site = str(item["site"])
        site_usage[site]["dispatch"] += delta if action == "dispatch" else 0.0
        site_usage[site]["inspect"] += delta if action == "inspect" else 0.0
        if action == "monitor":
            return
        region = policy["optimizer"]["site_region"][site]
        region_usage[region]["dispatch"] += delta if action == "dispatch" else 0.0
        region_usage[region]["inspect"] += delta if action == "inspect" else 0.0
        region_usage[region]["crew_hours"] += delta * action_hours(item, action, policy)

    def search(position: int) -> None:
        nonlocal best_actions, best_key, best_schedule_rows, best_part_rows
        if position == len(ordered):
            base_key = evaluate_plan(ordered, actions, policy)
            if best_key is not None and not better_base_key(base_key, best_key):
                return
            schedule_result = best_schedule(ordered, actions, policy)
            if schedule_result is None:
                return
            schedule_rows, part_rows, schedule_end, schedule_travel, part_transfer = schedule_result
            score_key = (
                base_key[0],
                base_key[1],
                base_key[2],
                base_key[3],
                -schedule_end.timestamp(),
                -schedule_travel,
                -part_transfer,
                base_key[4],
            )
            if better_plan(score_key, best_key):
                best_key = score_key
                best_actions = list(actions)
                best_schedule_rows = schedule_rows
                best_part_rows = part_rows
            return
        item = ordered[position]
        candidates = sorted(feasible_actions(item, policy), key=lambda action: (-action_utility(item, action, policy), action))
        for action in candidates:
            if not fits(item, action):
                continue
            apply(item, action, 1.0)
            actions.append(action)
            search(position + 1)
            actions.pop()
            apply(item, action, -1.0)

    search(0)
    assert best_actions is not None
    assert best_schedule_rows is not None
    assert best_part_rows is not None
    for item, action in zip(ordered, best_actions):
        item["action"] = action
        item["due_within_hours"] = int(policy["due_hours"][action])
        item["decision_value"] = action_utility(item, action, policy)
        item["reason"] = f"{item['top_factor']}:{item['risk_band']}"
    return best_schedule_rows, best_part_rows


def expected_scores(
    model_path: Path = MODEL_PATH,
    policy_path: Path = POLICY_PATH,
    calls_path: Path = CALLS_PATH,
    windows_path: Path = WINDOWS_PATH,
    history_path: Path = HISTORY_PATH,
    labels_path: Path = LABELS_PATH,
    capacity_path: Path = CAPACITY_PATH,
) -> list[dict[str, str | float | int]]:
    model, policy, calls, windows, history, _labels, capacity = load_bundle(
        model_path, policy_path, calls_path, windows_path, history_path, labels_path, capacity_path
    )
    items = [score_call(call, latest_window(call, windows), windows, history, model, policy) for call in calls]
    optimize_actions(items, policy, capacity)
    return items


def expected_schedule(
    model_path: Path = MODEL_PATH,
    policy_path: Path = POLICY_PATH,
    calls_path: Path = CALLS_PATH,
    windows_path: Path = WINDOWS_PATH,
    history_path: Path = HISTORY_PATH,
    labels_path: Path = LABELS_PATH,
    capacity_path: Path = CAPACITY_PATH,
) -> list[dict[str, object]]:
    model, policy, calls, windows, history, _labels, capacity = load_bundle(
        model_path, policy_path, calls_path, windows_path, history_path, labels_path, capacity_path
    )
    items = [score_call(call, latest_window(call, windows), windows, history, model, policy) for call in calls]
    schedule_rows, _part_rows = optimize_actions(items, policy, capacity)
    return schedule_rows


def expected_parts(
    model_path: Path = MODEL_PATH,
    policy_path: Path = POLICY_PATH,
    calls_path: Path = CALLS_PATH,
    windows_path: Path = WINDOWS_PATH,
    history_path: Path = HISTORY_PATH,
    labels_path: Path = LABELS_PATH,
    capacity_path: Path = CAPACITY_PATH,
) -> list[dict[str, object]]:
    model, policy, calls, windows, history, _labels, capacity = load_bundle(
        model_path, policy_path, calls_path, windows_path, history_path, labels_path, capacity_path
    )
    items = [score_call(call, latest_window(call, windows), windows, history, model, policy) for call in calls]
    _schedule_rows, part_rows = optimize_actions(items, policy, capacity)
    return part_rows


@pytest.fixture(scope="session")
def verifier_run(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run Go tests and the CLI in a verifier-owned output directory."""
    go_test = subprocess.run(["go", "test", "./..."], cwd=APP, text=True, capture_output=True, timeout=60)
    assert go_test.returncode == 0, go_test.stdout + go_test.stderr
    out_dir = tmp_path_factory.mktemp("fleetrisk-out")
    cmd = [
        "go",
        "run",
        "./cmd/fleetrisk",
        "--model",
        str(MODEL_PATH),
        "--policy",
        str(POLICY_PATH),
        "--calls",
        str(CALLS_PATH),
        "--windows",
        str(WINDOWS_PATH),
        "--history",
        str(HISTORY_PATH),
        "--labels",
        str(LABELS_PATH),
        "--capacity",
        str(CAPACITY_PATH),
        "--out-dir",
        str(out_dir),
    ]
    result = subprocess.run(cmd, cwd=APP, text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    return out_dir


def read_output_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_agent_left_required_reports_in_app_out() -> None:
    """Verify the requested report files were left in /app/out."""
    expected = {
        "scored_calls.csv",
        "maintenance_decisions.csv",
        "crew_schedule.csv",
        "parts_allocation.csv",
        "risk_manifest.json",
        "evaluation.json",
    }
    assert OUT_DIR.is_dir(), "/app/out was not created"
    assert expected.issubset({path.name for path in OUT_DIR.iterdir()})


def test_required_reports_have_consistent_row_counts() -> None:
    """Verify the report row counts match the fixed service-call input."""
    assert len(read_output_csv(OUT_DIR / "scored_calls.csv")) == len(expected_scores())
    assert len(read_output_csv(OUT_DIR / "maintenance_decisions.csv")) == len(expected_scores())
    assert len(read_output_csv(OUT_DIR / "crew_schedule.csv")) == len(expected_schedule())
    assert len(read_output_csv(OUT_DIR / "parts_allocation.csv")) == len(expected_parts())
    manifest = json.loads((OUT_DIR / "risk_manifest.json").read_text())
    evaluation = json.loads((OUT_DIR / "evaluation.json").read_text())
    assert manifest["row_count"] == len(expected_scores())
    assert evaluation["row_count"] == len(expected_scores())


def test_shipped_inputs_were_not_changed() -> None:
    """Verify the fixed CSV and JSON input files were not modified."""
    for path, expected_hash in ORIGINAL_INPUT_HASHES.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash, f"{path} was changed"


def test_scored_calls_match_model_contract(verifier_run: Path) -> None:
    """Verify scored_calls.csv matches the temporal features, ensemble scoring, and calibration math."""
    rows = read_output_csv(verifier_run / "scored_calls.csv")
    expected = expected_scores()
    assert len(rows) == len(expected)
    for row, want in zip(rows, expected):
        assert row["request_id"] == want["request_id"]
        assert row["asset_id"] == want["asset_id"]
        assert row["site"] == want["site"]
        assert row["opened_at"] == want["opened_at"]
        assert row["priority"] == want["priority"]
        assert row["raw_score"] == f"{want['raw_score']:.6f}"
        assert row["calibrated_risk"] == f"{want['calibrated_risk']:.6f}"
        assert row["downtime_risk"] == f"{want['downtime_risk']:.6f}"
        assert row["risk_band"] == want["risk_band"]
        assert row["action"] == want["action"]
        assert row["top_factor"] == want["top_factor"]


def test_decisions_are_sorted_and_actionable(verifier_run: Path) -> None:
    """Verify the decision CSV schema, ordering, optimized actions, due hours, and utility values."""
    rows = read_output_csv(verifier_run / "maintenance_decisions.csv")
    expected = sorted(expected_scores(), key=lambda item: (-float(item["calibrated_risk"]), str(item["request_id"])))
    assert [row["request_id"] for row in rows] == [item["request_id"] for item in expected]
    for row, want in zip(rows, expected):
        assert row["asset_id"] == want["asset_id"]
        assert row["action"] == want["action"]
        assert row["risk_band"] == want["risk_band"]
        assert row["calibrated_risk"] == f"{want['calibrated_risk']:.6f}"
        assert row["downtime_risk"] == f"{want['downtime_risk']:.6f}"
        assert int(row["due_within_hours"]) == want["due_within_hours"]
        assert row["decision_value"] == f"{want['decision_value']:.6f}"
        assert row["reason"] == want["reason"]


def test_crew_schedule_matches_exact_roster_plan(verifier_run: Path) -> None:
    """Verify crew_schedule.csv matches the exact crew, shift, travel, and due-time scheduler."""
    rows = read_output_csv(verifier_run / "crew_schedule.csv")
    expected = expected_schedule()
    assert [row["request_id"] for row in rows] == [str(item["request_id"]) for item in expected]
    for row, want in zip(rows, expected):
        assert row["crew_id"] == want["crew_id"]
        assert row["region"] == want["region"]
        assert row["site"] == want["site"]
        assert row["action"] == want["action"]
        assert row["start_at"] == format_utc(want["start_at"])
        assert row["end_at"] == format_utc(want["end_at"])
        assert row["travel_hours"] == f"{float(want['travel_hours']):.6f}"


def test_parts_allocation_matches_exact_inventory_plan(verifier_run: Path) -> None:
    """Verify parts_allocation.csv matches the exact inventory and transfer-aware scheduler."""
    rows = read_output_csv(verifier_run / "parts_allocation.csv")
    expected = expected_parts()
    assert [row["request_id"] for row in rows] == [str(item["request_id"]) for item in expected]
    for row, want in zip(rows, expected):
        assert row["part_id"] == want["part_id"]
        assert row["source_site"] == want["source_site"]
        assert row["dest_site"] == want["dest_site"]
        assert int(row["quantity"]) == want["quantity"]
        assert row["ready_at"] == format_utc(want["ready_at"])
        assert row["transfer_hours"] == f"{float(want['transfer_hours']):.6f}"


def test_manifest_records_inputs_and_outputs(verifier_run: Path) -> None:
    """Verify risk_manifest.json contains deterministic metadata and all input digests."""
    model, policy, calls, _windows, _history, _labels, _capacity = load_bundle()
    manifest = json.loads((verifier_run / "risk_manifest.json").read_text())
    assert manifest["generated_at"] == policy["report_generated_at"]
    assert manifest["model_id"] == model["model_id"]
    assert manifest["policy_id"] == policy["policy_id"]
    assert manifest["row_count"] == len(calls)
    assert manifest["output_files"] == [
        "scored_calls.csv",
        "maintenance_decisions.csv",
        "crew_schedule.csv",
        "parts_allocation.csv",
        "risk_manifest.json",
        "evaluation.json",
    ]
    expected_hashes = {
        "calls": CALLS_PATH,
        "windows": WINDOWS_PATH,
        "history": HISTORY_PATH,
        "labels": LABELS_PATH,
        "capacity": CAPACITY_PATH,
        "model": MODEL_PATH,
        "policy": POLICY_PATH,
    }
    assert set(manifest["input_sha256"]) == set(expected_hashes)
    for name, path in expected_hashes.items():
        assert manifest["input_sha256"][name] == hashlib.sha256(path.read_bytes()).hexdigest()


def evaluation_expectations() -> dict[str, object]:
    """Build expected evaluation pieces from labels and expected decisions."""
    _model, _policy, _calls, _windows, _history, labels, _capacity = load_bundle()
    expected = expected_scores()
    matrix = {"true_positive": 0, "false_positive": 0, "true_negative": 0, "false_negative": 0}
    site_counts: dict[str, dict[str, float]] = defaultdict(lambda: {"count": 0, "actions": 0, "failures": 0, "risk": 0.0})
    positive_actions = 0
    brier = 0.0
    for item in expected:
        label = labels[str(item["request_id"])]
        predicted = item["action"] in {"dispatch", "inspect"}
        positive_actions += int(predicted)
        if predicted and label == 1:
            matrix["true_positive"] += 1
        elif predicted and label == 0:
            matrix["false_positive"] += 1
        elif not predicted and label == 0:
            matrix["true_negative"] += 1
        else:
            matrix["false_negative"] += 1
        risk = float(item["calibrated_risk"])
        brier += (risk - label) ** 2
        site = site_counts[str(item["site"])]
        site["count"] += 1
        site["actions"] += int(predicted)
        site["failures"] += label
        site["risk"] += risk
    precision = matrix["true_positive"] / (matrix["true_positive"] + matrix["false_positive"])
    recall = matrix["true_positive"] / (matrix["true_positive"] + matrix["false_negative"])
    f1 = 2 * precision * recall / (precision + recall)
    return {
        "expected": expected,
        "labels": labels,
        "matrix": matrix,
        "site_counts": site_counts,
        "positive_actions": positive_actions,
        "brier": brier / len(expected),
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def test_evaluation_confusion_matrix_and_basic_metrics_match_labels(verifier_run: Path) -> None:
    """Verify classification metrics treat inspect and dispatch as positive actions."""
    evaluation = json.loads((verifier_run / "evaluation.json").read_text())
    want = evaluation_expectations()
    expected = want["expected"]
    assert evaluation["row_count"] == len(expected)
    assert evaluation["positive_action_count"] == want["positive_actions"]
    assert evaluation["confusion_matrix"] == want["matrix"]
    assert evaluation["metrics"]["precision"] == pytest.approx(want["precision"])
    assert evaluation["metrics"]["recall"] == pytest.approx(want["recall"])
    assert evaluation["metrics"]["f1"] == pytest.approx(want["f1"])
    assert evaluation["metrics"]["brier_score"] == pytest.approx(want["brier"])


def test_evaluation_ranking_metrics_match_labels(verifier_run: Path) -> None:
    """Verify ROC AUC and average precision use calibrated risk ordering."""
    evaluation = json.loads((verifier_run / "evaluation.json").read_text())
    want = evaluation_expectations()
    expected = want["expected"]
    labels = want["labels"]
    assert evaluation["metrics"]["roc_auc"] == pytest.approx(roc_auc(expected, labels))
    assert evaluation["metrics"]["average_precision"] == pytest.approx(average_precision(expected, labels))


def test_evaluation_site_metrics_match_labels(verifier_run: Path) -> None:
    """Verify site_metrics aggregates counts, actions, failures, and mean risk per site."""
    evaluation = json.loads((verifier_run / "evaluation.json").read_text())
    site_counts = evaluation_expectations()["site_counts"]
    for site, values in site_counts.items():
        got = evaluation["site_metrics"][site]
        assert got["count"] == values["count"]
        assert got["positive_action_count"] == values["actions"]
        assert got["observed_failure_count"] == values["failures"]
        assert got["mean_calibrated_risk"] == pytest.approx(values["risk"] / values["count"])


def roc_auc(items: list[dict[str, str | float | int]], labels: dict[str, int]) -> float:
    scored = sorted((float(item["calibrated_risk"]), labels[str(item["request_id"])]) for item in items)
    positives = sum(label for _score, label in scored)
    negatives = len(scored) - positives
    if positives == 0 or negatives == 0:
        return 0.0
    rank_sum = 0.0
    index = 0
    while index < len(scored):
        end = index + 1
        while end < len(scored) and scored[end][0] == scored[index][0]:
            end += 1
        average_rank = (index + 1 + end) / 2.0
        rank_sum += average_rank * sum(label for _score, label in scored[index:end])
        index = end
    return (rank_sum - positives * (positives + 1) / 2.0) / (positives * negatives)


def average_precision(items: list[dict[str, str | float | int]], labels: dict[str, int]) -> float:
    ordered = sorted(items, key=lambda item: (-float(item["calibrated_risk"]), str(item["request_id"])))
    positives = sum(labels[str(item["request_id"])] for item in ordered)
    if positives == 0:
        return 0.0
    found = 0
    precision_sum = 0.0
    for rank, item in enumerate(ordered, start=1):
        if labels[str(item["request_id"])] == 1:
            found += 1
            precision_sum += found / rank
    return precision_sum / positives


def test_top_factor_uses_calibrated_integrated_attribution(tmp_path: Path) -> None:
    """Verify top_factor uses calibrated integrated-gradient attribution, not raw weight contribution."""
    model = {
        "model_id": "attribution-counterexample",
        "feature_params": {
            "trend_lookback_hours": 168.0,
            "temp_ewma_half_life_hours": 48.0,
            "history_lookback_days": 120.0,
            "history_half_life_days": 21.0,
        },
        "heads": {
            "failure": {
                "intercept": 0.0,
                "weights": {"urgent_flag": 6.0},
                "calibration": [{"raw": 0.0, "calibrated": 0.20}, {"raw": 1.0, "calibrated": 0.20}],
            },
            "downtime": {
                "intercept": 0.0,
                "weights": {"leak_flag": 1.0},
                "calibration": [{"raw": 0.0, "calibrated": 0.0}, {"raw": 1.0, "calibrated": 1.0}],
            },
        },
        "blend_by_asset_type": {"pump": {"failure": 0.80, "downtime": 0.20}},
        "asset_types": {
            "pump": {
                "temp_limit_c": 80.0,
                "max_vibration_mm_s": 7.0,
                "nominal_pressure_kpa": 310.0,
                "current_mean_a": 18.0,
                "current_std_a": 3.0,
                "impute_temp_c": 75.0,
            }
        },
    }
    policy = {
        "policy_id": "attribution-counterexample-policy",
        "report_generated_at": "2026-06-15T12:00:00Z",
        "thresholds": {"dispatch": 0.68, "inspect": 0.42, "watch": 0.25, "urgent_inspect_floor": 0.35},
        "due_hours": {"dispatch": 12, "inspect": 48, "monitor": 168},
        "optimizer": {
            "risk_effect": {"dispatch": 1.0, "inspect": 0.5, "monitor": 0.0},
            "downtime_effect": {"dispatch": 0.5, "inspect": 0.2, "monitor": 0.0},
            "action_cost": {"dispatch": 0.1, "inspect": 0.05, "monitor": 0.0},
            "minimum_risk": {"dispatch": 0.90, "inspect": 0.90, "monitor": 0.0},
            "site_region": {"LAB": "lab-region"},
            "regional_limits": {"lab-region": {"dispatch_slots": 1, "inspect_slots": 1, "crew_hours": 4.0}},
            "action_hours": {
                "dispatch": {"pump": 2.0},
                "inspect": {"pump": 1.0},
                "monitor": {"pump": 0.0},
            },
            "priority_bonus": {"urgent": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0}},
        },
    }
    paths = {
        "model": tmp_path / "model.json",
        "policy": tmp_path / "policy.json",
        "calls": tmp_path / "calls.csv",
        "windows": tmp_path / "windows.csv",
        "history": tmp_path / "history.csv",
        "labels": tmp_path / "labels.csv",
        "capacity": tmp_path / "capacity.csv",
    }
    paths["model"].write_text(json.dumps(model))
    paths["policy"].write_text(json.dumps(policy))
    write_csv(
        paths["calls"],
        [
            {
                "request_id": "IG-1",
                "asset_id": "IG-A",
                "asset_type": "pump",
                "site": "LAB",
                "opened_at": "2026-04-09T08:00:00Z",
                "priority": "urgent",
                "technician_hours": "0",
                "notes_code": "LEAK",
            }
        ],
    )
    write_csv(
        paths["windows"],
        [
            {
                "asset_id": "IG-A",
                "window_end": "2026-04-09T07:00:00Z",
                "temp_c": "75",
                "vibration_mm_s": "3",
                "pressure_kpa": "310",
                "current_a": "18",
                "runtime_hours": "100",
            }
        ],
    )
    write_csv(paths["history"], [{"asset_id": "IG-A", "event_time": "2026-04-01T00:00:00Z", "event_type": "inspection", "severity": "1"}])
    write_csv(paths["labels"], [{"request_id": "IG-1", "failure_within_30d": "0"}])
    write_csv(paths["capacity"], [{"site": "LAB", "dispatch_slots": "1", "inspect_slots": "1"}])
    out_dir = tmp_path / "out"
    result = subprocess.run(
        [
            "go",
            "run",
            "./cmd/fleetrisk",
            "--model",
            str(paths["model"]),
            "--policy",
            str(paths["policy"]),
            "--calls",
            str(paths["calls"]),
            "--windows",
            str(paths["windows"]),
            "--history",
            str(paths["history"]),
            "--labels",
            str(paths["labels"]),
            "--capacity",
            str(paths["capacity"]),
            "--out-dir",
            str(out_dir),
        ],
        cwd=APP,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    rows = read_output_csv(out_dir / "scored_calls.csv")
    assert rows[0]["top_factor"] == "leak_flag"


def test_capacity_optimizer_uses_exact_global_region_plan(tmp_path: Path) -> None:
    """Verify shared regional capacity can override each site's locally best dispatch choice."""
    model = {
        "model_id": "optimizer-counterexample",
        "feature_params": {
            "trend_lookback_hours": 168.0,
            "temp_ewma_half_life_hours": 48.0,
            "history_lookback_days": 120.0,
            "history_half_life_days": 21.0,
        },
        "heads": {
            "failure": {
                "intercept": -2.0,
                "weights": {"urgent_flag": 4.0},
                "calibration": [{"raw": 0.0, "calibrated": 0.0}, {"raw": 1.0, "calibrated": 1.0}],
            },
            "downtime": {
                "intercept": -2.0,
                "weights": {"leak_flag": 5.0, "heat_flag": 2.0},
                "calibration": [{"raw": 0.0, "calibrated": 0.0}, {"raw": 1.0, "calibrated": 1.0}],
            },
        },
        "blend_by_asset_type": {"pump": {"failure": 1.0, "downtime": 0.0}},
        "asset_types": {
            "pump": {
                "temp_limit_c": 80.0,
                "max_vibration_mm_s": 7.0,
                "nominal_pressure_kpa": 310.0,
                "current_mean_a": 18.0,
                "current_std_a": 3.0,
                "impute_temp_c": 75.0,
            }
        },
    }
    policy = {
        "policy_id": "optimizer-counterexample-policy",
        "report_generated_at": "2026-06-15T12:00:00Z",
        "thresholds": {"dispatch": 0.68, "inspect": 0.42, "watch": 0.25, "urgent_inspect_floor": 0.1},
        "due_hours": {"dispatch": 12, "inspect": 48, "monitor": 168},
        "optimizer": {
            "risk_effect": {"dispatch": 0.40, "inspect": 0.80, "monitor": 0.0},
            "downtime_effect": {"dispatch": 1.20, "inspect": 0.05, "monitor": 0.0},
            "action_cost": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0},
            "minimum_risk": {"dispatch": 0.10, "inspect": 0.10, "monitor": 0.0},
            "site_region": {"PHX": "metro", "DEN": "metro"},
            "regional_limits": {"metro": {"dispatch_slots": 1, "inspect_slots": 1, "crew_hours": 10.0}},
            "action_hours": {
                "dispatch": {"pump": 2.0},
                "inspect": {"pump": 1.0},
                "monitor": {"pump": 0.0},
            },
            "crew_roster": [
                {
                    "crew_id": "METRO-1",
                    "region": "metro",
                    "home_site": "PHX",
                    "shift_start": "2026-06-15T12:00:00Z",
                    "shift_end": "2026-06-15T20:00:00Z",
                    "max_continuous_hours": 4.0,
                },
                {
                    "crew_id": "METRO-2",
                    "region": "metro",
                    "home_site": "DEN",
                    "shift_start": "2026-06-15T12:00:00Z",
                    "shift_end": "2026-06-15T20:00:00Z",
                    "max_continuous_hours": 4.0,
                },
            ],
            "break_hours": 0.75,
            "travel_hours": {
                "metro": {
                    "PHX": {"PHX": 0.0, "DEN": 1.0},
                    "DEN": {"PHX": 1.0, "DEN": 0.0},
                }
            },
            "priority_bonus": {
                "urgent": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0},
                "routine": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0},
            },
        },
    }
    paths = {
        "model": tmp_path / "model.json",
        "policy": tmp_path / "policy.json",
        "calls": tmp_path / "calls.csv",
        "windows": tmp_path / "windows.csv",
        "history": tmp_path / "history.csv",
        "labels": tmp_path / "labels.csv",
        "capacity": tmp_path / "capacity.csv",
    }
    paths["model"].write_text(json.dumps(model))
    paths["policy"].write_text(json.dumps(policy))
    write_csv(
        paths["calls"],
        [
            {
                "request_id": "S-A",
                "asset_id": "A-1",
                "asset_type": "pump",
                "site": "PHX",
                "opened_at": "2026-04-09T08:00:00Z",
                "priority": "urgent",
                "technician_hours": "0",
                "notes_code": "CHECK",
            },
            {
                "request_id": "S-B",
                "asset_id": "B-1",
                "asset_type": "pump",
                "site": "DEN",
                "opened_at": "2026-04-09T08:05:00Z",
                "priority": "routine",
                "technician_hours": "0",
                "notes_code": "LEAK",
            },
            {
                "request_id": "S-C",
                "asset_id": "C-1",
                "asset_type": "pump",
                "site": "DEN",
                "opened_at": "2026-04-09T08:10:00Z",
                "priority": "routine",
                "technician_hours": "0",
                "notes_code": "HEAT",
            },
        ],
    )
    write_csv(
        paths["windows"],
        [
            {
                "asset_id": "A-1",
                "window_end": "2026-04-09T07:00:00Z",
                "temp_c": "75",
                "vibration_mm_s": "3",
                "pressure_kpa": "310",
                "current_a": "18",
                "runtime_hours": "100",
            },
            {
                "asset_id": "B-1",
                "window_end": "2026-04-09T07:00:00Z",
                "temp_c": "75",
                "vibration_mm_s": "3",
                "pressure_kpa": "310",
                "current_a": "18",
                "runtime_hours": "100",
            },
            {
                "asset_id": "C-1",
                "window_end": "2026-04-09T07:00:00Z",
                "temp_c": "75",
                "vibration_mm_s": "3",
                "pressure_kpa": "310",
                "current_a": "18",
                "runtime_hours": "100",
            },
        ],
    )
    write_csv(paths["history"], [{"asset_id": "A-1", "event_time": "2026-04-01T00:00:00Z", "event_type": "inspection", "severity": "1"}])
    write_csv(
        paths["labels"],
        [
            {"request_id": "S-A", "failure_within_30d": "1"},
            {"request_id": "S-B", "failure_within_30d": "0"},
            {"request_id": "S-C", "failure_within_30d": "0"},
        ],
    )
    write_csv(
        paths["capacity"],
        [
            {"site": "PHX", "dispatch_slots": "1", "inspect_slots": "1"},
            {"site": "DEN", "dispatch_slots": "1", "inspect_slots": "1"},
        ],
    )
    out_dir = tmp_path / "out"
    result = subprocess.run(
        [
            "go",
            "run",
            "./cmd/fleetrisk",
            "--model",
            str(paths["model"]),
            "--policy",
            str(paths["policy"]),
            "--calls",
            str(paths["calls"]),
            "--windows",
            str(paths["windows"]),
            "--history",
            str(paths["history"]),
            "--labels",
            str(paths["labels"]),
            "--capacity",
            str(paths["capacity"]),
            "--out-dir",
            str(out_dir),
        ],
        cwd=APP,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    rows = {row["request_id"]: row for row in read_output_csv(out_dir / "maintenance_decisions.csv")}
    assert rows["S-B"]["action"] == "dispatch"
    assert rows["S-A"]["action"] == "inspect"
    assert rows["S-C"]["action"] == "monitor"
    assert float(rows["S-B"]["decision_value"]) > float(rows["S-A"]["decision_value"])


def test_crew_schedule_inserts_breaks_for_continuous_work_limit(tmp_path: Path) -> None:
    """Verify the roster scheduler delays work after a crew exceeds continuous action hours."""
    model = {
        "model_id": "crew-break-counterexample",
        "feature_params": {
            "trend_lookback_hours": 168.0,
            "temp_ewma_half_life_hours": 48.0,
            "history_lookback_days": 120.0,
            "history_half_life_days": 21.0,
        },
        "heads": {
            "failure": {
                "intercept": 3.0,
                "weights": {},
                "calibration": [{"raw": 0.0, "calibrated": 0.0}, {"raw": 1.0, "calibrated": 1.0}],
            },
            "downtime": {
                "intercept": 0.0,
                "weights": {},
                "calibration": [{"raw": 0.0, "calibrated": 0.0}, {"raw": 1.0, "calibrated": 1.0}],
            },
        },
        "blend_by_asset_type": {"pump": {"failure": 1.0, "downtime": 0.0}},
        "asset_types": {
            "pump": {
                "temp_limit_c": 80.0,
                "max_vibration_mm_s": 7.0,
                "nominal_pressure_kpa": 310.0,
                "current_mean_a": 18.0,
                "current_std_a": 3.0,
                "impute_temp_c": 75.0,
            }
        },
    }
    policy = {
        "policy_id": "crew-break-counterexample-policy",
        "report_generated_at": "2026-06-15T12:00:00Z",
        "thresholds": {"dispatch": 0.50, "inspect": 0.98, "watch": 0.25, "urgent_inspect_floor": 0.98},
        "due_hours": {"dispatch": 12, "inspect": 48, "monitor": 168},
        "optimizer": {
            "risk_effect": {"dispatch": 1.0, "inspect": 0.1, "monitor": 0.0},
            "downtime_effect": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0},
            "action_cost": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0},
            "minimum_risk": {"dispatch": 0.10, "inspect": 0.98, "monitor": 0.0},
            "site_region": {"LAB": "lab-region"},
            "regional_limits": {"lab-region": {"dispatch_slots": 2, "inspect_slots": 0, "crew_hours": 4.0}},
            "action_hours": {
                "dispatch": {"pump": 2.0},
                "inspect": {"pump": 1.0},
                "monitor": {"pump": 0.0},
            },
            "crew_roster": [
                {
                    "crew_id": "LAB-1",
                    "region": "lab-region",
                    "home_site": "LAB",
                    "shift_start": "2026-06-15T12:00:00Z",
                    "shift_end": "2026-06-15T20:00:00Z",
                    "max_continuous_hours": 3.0,
                }
            ],
            "break_hours": 0.75,
            "travel_hours": {"lab-region": {"LAB": {"LAB": 0.0}}},
            "priority_bonus": {
                "urgent": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0},
                "routine": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0},
            },
        },
    }
    paths = {
        "model": tmp_path / "model.json",
        "policy": tmp_path / "policy.json",
        "calls": tmp_path / "calls.csv",
        "windows": tmp_path / "windows.csv",
        "history": tmp_path / "history.csv",
        "labels": tmp_path / "labels.csv",
        "capacity": tmp_path / "capacity.csv",
    }
    paths["model"].write_text(json.dumps(model))
    paths["policy"].write_text(json.dumps(policy))
    write_csv(
        paths["calls"],
        [
            {
                "request_id": "BR-1",
                "asset_id": "BR-A",
                "asset_type": "pump",
                "site": "LAB",
                "opened_at": "2026-04-09T08:00:00Z",
                "priority": "routine",
                "technician_hours": "0",
                "notes_code": "CHECK",
            },
            {
                "request_id": "BR-2",
                "asset_id": "BR-B",
                "asset_type": "pump",
                "site": "LAB",
                "opened_at": "2026-04-09T08:05:00Z",
                "priority": "routine",
                "technician_hours": "0",
                "notes_code": "CHECK",
            },
        ],
    )
    write_csv(
        paths["windows"],
        [
            {
                "asset_id": "BR-A",
                "window_end": "2026-04-09T07:00:00Z",
                "temp_c": "75",
                "vibration_mm_s": "3",
                "pressure_kpa": "310",
                "current_a": "18",
                "runtime_hours": "100",
            },
            {
                "asset_id": "BR-B",
                "window_end": "2026-04-09T07:00:00Z",
                "temp_c": "75",
                "vibration_mm_s": "3",
                "pressure_kpa": "310",
                "current_a": "18",
                "runtime_hours": "100",
            },
        ],
    )
    write_csv(
        paths["history"],
        [
            {"asset_id": "BR-A", "event_time": "2026-04-01T00:00:00Z", "event_type": "inspection", "severity": "1"},
            {"asset_id": "BR-B", "event_time": "2026-04-01T00:00:00Z", "event_type": "inspection", "severity": "1"},
        ],
    )
    write_csv(
        paths["labels"],
        [
            {"request_id": "BR-1", "failure_within_30d": "0"},
            {"request_id": "BR-2", "failure_within_30d": "0"},
        ],
    )
    write_csv(paths["capacity"], [{"site": "LAB", "dispatch_slots": "2", "inspect_slots": "0"}])
    out_dir = tmp_path / "out"
    result = subprocess.run(
        [
            "go",
            "run",
            "./cmd/fleetrisk",
            "--model",
            str(paths["model"]),
            "--policy",
            str(paths["policy"]),
            "--calls",
            str(paths["calls"]),
            "--windows",
            str(paths["windows"]),
            "--history",
            str(paths["history"]),
            "--labels",
            str(paths["labels"]),
            "--capacity",
            str(paths["capacity"]),
            "--out-dir",
            str(out_dir),
        ],
        cwd=APP,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    decisions = {row["request_id"]: row["action"] for row in read_output_csv(out_dir / "maintenance_decisions.csv")}
    assert decisions == {"BR-1": "dispatch", "BR-2": "dispatch"}
    schedule = read_output_csv(out_dir / "crew_schedule.csv")
    assert [(row["request_id"], row["start_at"], row["end_at"]) for row in schedule] == [
        ("BR-1", "2026-06-15T12:00:00Z", "2026-06-15T14:00:00Z"),
        ("BR-2", "2026-06-15T14:45:00Z", "2026-06-15T16:45:00Z"),
    ]


def test_parts_transfer_ready_time_delays_schedule(tmp_path: Path) -> None:
    """Verify part transfer readiness can delay an otherwise crew-ready dispatch."""
    model = {
        "model_id": "parts-transfer-counterexample",
        "feature_params": {
            "trend_lookback_hours": 168.0,
            "temp_ewma_half_life_hours": 48.0,
            "history_lookback_days": 120.0,
            "history_half_life_days": 21.0,
        },
        "heads": {
            "failure": {
                "intercept": 3.0,
                "weights": {},
                "calibration": [{"raw": 0.0, "calibrated": 0.0}, {"raw": 1.0, "calibrated": 1.0}],
            },
            "downtime": {
                "intercept": 0.0,
                "weights": {},
                "calibration": [{"raw": 0.0, "calibrated": 0.0}, {"raw": 1.0, "calibrated": 1.0}],
            },
        },
        "blend_by_asset_type": {"pump": {"failure": 1.0, "downtime": 0.0}},
        "asset_types": {
            "pump": {
                "temp_limit_c": 80.0,
                "max_vibration_mm_s": 7.0,
                "nominal_pressure_kpa": 310.0,
                "current_mean_a": 18.0,
                "current_std_a": 3.0,
                "impute_temp_c": 75.0,
            }
        },
    }
    policy = {
        "policy_id": "parts-transfer-counterexample-policy",
        "report_generated_at": "2026-06-15T12:00:00Z",
        "thresholds": {"dispatch": 0.50, "inspect": 0.98, "watch": 0.25, "urgent_inspect_floor": 0.98},
        "due_hours": {"dispatch": 12, "inspect": 48, "monitor": 168},
        "optimizer": {
            "risk_effect": {"dispatch": 1.0, "inspect": 0.1, "monitor": 0.0},
            "downtime_effect": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0},
            "action_cost": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0},
            "minimum_risk": {"dispatch": 0.10, "inspect": 0.98, "monitor": 0.0},
            "site_region": {"DEPOT": "lab-region", "FIELD": "lab-region"},
            "regional_limits": {"lab-region": {"dispatch_slots": 1, "inspect_slots": 0, "crew_hours": 1.0}},
            "action_hours": {
                "dispatch": {"pump": 1.0},
                "inspect": {"pump": 1.0},
                "monitor": {"pump": 0.0},
            },
            "action_parts": {"dispatch": {"pump": {"sealkit": 1}}, "inspect": {}, "monitor": {}},
            "parts_inventory": [
                {"site": "DEPOT", "part_id": "sealkit", "on_hand": 1, "reserve_min": 0},
                {"site": "FIELD", "part_id": "sealkit", "on_hand": 0, "reserve_min": 0},
            ],
            "crew_roster": [
                {
                    "crew_id": "FIELD-1",
                    "region": "lab-region",
                    "home_site": "FIELD",
                    "shift_start": "2026-06-15T12:00:00Z",
                    "shift_end": "2026-06-15T20:00:00Z",
                    "max_continuous_hours": 4.0,
                }
            ],
            "break_hours": 0.75,
            "part_transfer_hours": {
                "lab-region": {
                    "DEPOT": {"DEPOT": 0.0, "FIELD": 2.0},
                    "FIELD": {"DEPOT": 2.0, "FIELD": 0.0},
                }
            },
            "travel_hours": {"lab-region": {"FIELD": {"FIELD": 0.0}}},
            "priority_bonus": {
                "urgent": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0},
                "routine": {"dispatch": 0.0, "inspect": 0.0, "monitor": 0.0},
            },
        },
    }
    paths = {
        "model": tmp_path / "model.json",
        "policy": tmp_path / "policy.json",
        "calls": tmp_path / "calls.csv",
        "windows": tmp_path / "windows.csv",
        "history": tmp_path / "history.csv",
        "labels": tmp_path / "labels.csv",
        "capacity": tmp_path / "capacity.csv",
    }
    paths["model"].write_text(json.dumps(model))
    paths["policy"].write_text(json.dumps(policy))
    write_csv(
        paths["calls"],
        [
            {
                "request_id": "PT-1",
                "asset_id": "PT-A",
                "asset_type": "pump",
                "site": "FIELD",
                "opened_at": "2026-04-09T08:00:00Z",
                "priority": "routine",
                "technician_hours": "0",
                "notes_code": "CHECK",
            }
        ],
    )
    write_csv(
        paths["windows"],
        [
            {
                "asset_id": "PT-A",
                "window_end": "2026-04-09T07:00:00Z",
                "temp_c": "75",
                "vibration_mm_s": "3",
                "pressure_kpa": "310",
                "current_a": "18",
                "runtime_hours": "100",
            }
        ],
    )
    write_csv(paths["history"], [{"asset_id": "PT-A", "event_time": "2026-04-01T00:00:00Z", "event_type": "inspection", "severity": "1"}])
    write_csv(paths["labels"], [{"request_id": "PT-1", "failure_within_30d": "0"}])
    write_csv(paths["capacity"], [{"site": "FIELD", "dispatch_slots": "1", "inspect_slots": "0"}])
    out_dir = tmp_path / "out"
    result = subprocess.run(
        [
            "go",
            "run",
            "./cmd/fleetrisk",
            "--model",
            str(paths["model"]),
            "--policy",
            str(paths["policy"]),
            "--calls",
            str(paths["calls"]),
            "--windows",
            str(paths["windows"]),
            "--history",
            str(paths["history"]),
            "--labels",
            str(paths["labels"]),
            "--capacity",
            str(paths["capacity"]),
            "--out-dir",
            str(out_dir),
        ],
        cwd=APP,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    schedule = read_output_csv(out_dir / "crew_schedule.csv")
    assert [(row["request_id"], row["start_at"], row["end_at"]) for row in schedule] == [
        ("PT-1", "2026-06-15T14:00:00Z", "2026-06-15T15:00:00Z")
    ]
    parts = read_output_csv(out_dir / "parts_allocation.csv")
    assert parts == [
        {
            "request_id": "PT-1",
            "part_id": "sealkit",
            "source_site": "DEPOT",
            "dest_site": "FIELD",
            "quantity": "1",
            "ready_at": "2026-06-15T14:00:00Z",
            "transfer_hours": "2.000000",
        }
    ]


def test_missing_sensor_window_fails_with_clear_error(tmp_path: Path) -> None:
    """Verify the CLI fails non-zero when a call has no usable sensor window."""
    bad_calls = tmp_path / "calls.csv"
    bad_calls.write_text(
        "request_id,asset_id,asset_type,site,opened_at,priority,technician_hours,notes_code\n"
        "R-MISSING,Z-99,pump,PHX,2026-04-07T08:30:00Z,routine,1.0,CHECK\n"
    )
    result = subprocess.run(
        [
            "go",
            "run",
            "./cmd/fleetrisk",
            "--model",
            str(MODEL_PATH),
            "--policy",
            str(POLICY_PATH),
            "--calls",
            str(bad_calls),
            "--windows",
            str(WINDOWS_PATH),
            "--history",
            str(HISTORY_PATH),
            "--labels",
            str(LABELS_PATH),
            "--capacity",
            str(CAPACITY_PATH),
            "--out-dir",
            str(tmp_path / "out"),
        ],
        cwd=APP,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "ERROR:" in result.stderr
    assert "no sensor window" in result.stderr
