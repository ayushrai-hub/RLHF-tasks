import copy
import json
import math
import random
import subprocess
from pathlib import Path


APP = Path("/app")
BINARY = Path("/tmp/tide-harmonic-forecaster")
ORIGINAL_MODEL = (APP / "model.json").read_text()
ORIGINAL_GAUGES = (APP / "gauges.jsonl").read_text()


def ensure_binary():
    """Build the candidate binary once for all dynamic verifier cases."""
    if not BINARY.exists():
        subprocess.run(["go", "build", "-o", str(BINARY), "."], cwd=APP, check=True, timeout=90)


def write_case(model, gauges):
    """Write a model and gauge set into the application input paths."""
    (APP / "model.json").write_text(json.dumps(model, indent=2) + "\n")
    (APP / "gauges.jsonl").write_text("\n".join(json.dumps(g, sort_keys=True) for g in gauges) + "\n")
    out = APP / "output" / "forecast.json"
    if out.exists():
        out.unlink()


def run_case(model, gauges):
    """Run the candidate program for one generated case and parse its report."""
    ensure_binary()
    write_case(model, gauges)
    subprocess.run([str(BINARY)], cwd=APP, check=True, timeout=10)
    out = APP / "output" / "forecast.json"
    assert out.exists(), "expected /app/output/forecast.json"
    return json.loads(out.read_text())


def fmt(value):
    """Format numeric report fields using the required six decimal places."""
    return f"{value:.6f}"


def base_model():
    """Return the baseline harmonic model used by public and generated cases."""
    return {
        "start_min": 0,
        "end_min": 720,
        "step_min": 60,
        "datum_m": 1.35,
        "flood_threshold_m": 2.35,
        "low_threshold_m": 0.45,
        "turn_min_delta_m": 0.08,
        "constituents": [
            {"name": "M2", "amplitude_m": 0.92, "speed_deg_per_hour": 28.9841042, "phase_deg": 12.0, "nodal_factor": 1.04, "epoch_min": 0},
            {"name": "S2", "amplitude_m": 0.31, "speed_deg_per_hour": 30.0, "phase_deg": 84.0, "nodal_factor": 0.97, "epoch_min": 0},
            {"name": "K1", "amplitude_m": 0.18, "speed_deg_per_hour": 15.0410686, "phase_deg": 211.0, "nodal_factor": 1.02, "epoch_min": -30},
        ],
        "segments": [
            {"id": "harbor", "flood_threshold_m": 2.28, "low_threshold_m": 0.52, "crew_cost": 2},
            {"id": "outer", "flood_threshold_m": 2.42, "low_threshold_m": 0.38, "crew_cost": 1},
        ],
        "calibration_events": [
            {"target": "*", "start_min": 180, "end_min": 300, "level_shift_m": -0.06, "flood_threshold_shift_m": -0.04, "low_threshold_shift_m": 0.03, "draft_shift_m": 0.00},
            {"target": "harbor", "start_min": 240, "end_min": 420, "level_shift_m": 0.05, "flood_threshold_shift_m": -0.02, "low_threshold_shift_m": 0.01, "draft_shift_m": 0.04},
            {"target": "creek-c", "start_min": 60, "end_min": 240, "level_shift_m": -0.03, "flood_threshold_shift_m": 0.00, "low_threshold_shift_m": 0.02, "draft_shift_m": -0.02},
        ],
        "closures": [
            {"gauge_id": "harbor-a", "start_min": 300, "end_min": 360},
            {"gauge_id": "creek-c", "start_min": 120, "end_min": 180},
        ],
        "blackouts": [
            {"segment": "outer", "start_min": 60, "end_min": 120},
        ],
        "operations": {
            "min_under_keel_m": 0.42,
            "flood_buffer_m": 0.18,
            "max_slope_m_per_hour": 0.58,
            "min_window_min": 120,
            "target_level_m": 1.45,
            "route_handoff_penalty_m": 0.05,
            "route_min_gap_min": 0,
            "route_max_layover_min": 240,
            "route_no_repeat_gauge": True,
            "route_max_total_target_error_m": 2.5,
        },
        "routes": [
            {"id": "harbor-outer", "segments": ["harbor", "outer"], "handoff_penalty_m": 0.07, "checkpoints": [{"index": 1, "earliest_start_min": 240, "latest_end_min": 720, "required_gauge_id": ""}], "forbidden_transitions": [{"from_gauge_id": "harbor-a", "to_gauge_id": "outer-b"}]},
            {"id": "harbor-creek", "segments": ["harbor", "creek"], "checkpoints": [{"index": 0, "earliest_start_min": 0, "latest_end_min": 420, "required_gauge_id": "harbor-a"}], "forbidden_transitions": [{"from_gauge_id": "", "to_gauge_id": "creek-c"}]},
        ],
    }


def base_gauges():
    """Return the baseline gauge set with multiple segments and priorities."""
    return [
        {"id": "harbor-a", "segment": "harbor", "offset_m": 0.08, "scale": 1.03, "drift_m_per_day": 0.018, "phase_lag_min": 8, "draft_m": 0.72, "priority": 3, "crew_capacity": 2},
        {"id": "outer-b", "segment": "outer", "offset_m": -0.05, "scale": 0.96, "drift_m_per_day": -0.010, "phase_lag_min": -12, "draft_m": 0.66, "priority": 2, "crew_capacity": 1},
        {"id": "creek-c", "segment": "creek", "offset_m": 0.14, "scale": 0.88, "drift_m_per_day": 0.006, "phase_lag_min": 24, "draft_m": 0.58, "priority": 4, "crew_capacity": 1},
    ]


def level_at(model, gauge, t):
    """Compute the unrounded expected level for one gauge at one sample time."""
    level_shift, _, _, _ = calibration_shifts(model, gauge, t)
    level = model["datum_m"] + gauge["offset_m"] + gauge["drift_m_per_day"] * ((t - model["start_min"]) / 1440.0) + level_shift
    for c in model["constituents"]:
        angle = c["speed_deg_per_hour"] * ((t + gauge["phase_lag_min"] - c["epoch_min"]) / 60.0) + c["phase_deg"]
        level += gauge["scale"] * c["amplitude_m"] * c["nodal_factor"] * math.cos(math.radians(angle))
    return level


def calibration_shifts(model, gauge, t):
    """Sum every active calibration event that targets the gauge, its segment, or every gauge."""
    level_shift = 0.0
    flood_shift = 0.0
    low_shift = 0.0
    draft_shift = 0.0
    for event in model.get("calibration_events", []):
        if not event["start_min"] <= t <= event["end_min"]:
            continue
        target = event["target"]
        if target not in ("*", gauge["id"], gauge["segment"]):
            continue
        level_shift += event.get("level_shift_m", 0.0)
        flood_shift += event.get("flood_threshold_shift_m", 0.0)
        low_shift += event.get("low_threshold_shift_m", 0.0)
        draft_shift += event.get("draft_shift_m", 0.0)
    return level_shift, flood_shift, low_shift, draft_shift


def thresholds(model, gauge, t):
    """Resolve segment-specific thresholds or fall back to model defaults."""
    _, flood_shift, low_shift, _ = calibration_shifts(model, gauge, t)
    for seg in model["segments"]:
        if seg["id"] == gauge["segment"]:
            return seg["flood_threshold_m"] + flood_shift, seg["low_threshold_m"] + low_shift
    return model["flood_threshold_m"] + flood_shift, model["low_threshold_m"] + low_shift


def build_alerts(model, gauge, rows, kind):
    """Build expected flood or low alert intervals from sampled rows."""
    def active(row):
        """Return whether a sampled row is inside the requested alert kind."""
        flood, low = thresholds(model, gauge, row["time_min"])
        threshold = flood if kind == "flood" else low
        return row["level"] >= threshold if kind == "flood" else row["level"] <= threshold

    alerts = []
    i = 0
    while i < len(rows):
        if not active(rows[i]):
            i += 1
            continue
        start = i
        best = i
        while i + 1 < len(rows) and active(rows[i + 1]):
            i += 1
            if kind == "flood":
                if rows[i]["level"] > rows[best]["level"]:
                    best = i
            elif rows[i]["level"] < rows[best]["level"]:
                best = i
        alerts.append({
            "gauge_id": gauge["id"],
            "kind": kind,
            "start_min": rows[start]["time_min"],
            "end_min": rows[i]["time_min"],
            "extreme_time_min": rows[best]["time_min"],
            "extreme_level_m": fmt(rows[best]["level"]),
        })
        i += 1
    return alerts


def build_turns(model, gauge, rows):
    """Build expected interior turning points using the configured delta."""
    turns = []
    delta = model["turn_min_delta_m"]
    for i in range(1, len(rows) - 1):
        prev_level = rows[i - 1]["level"]
        level = rows[i]["level"]
        next_level = rows[i + 1]["level"]
        if level - prev_level >= delta and level - next_level >= delta:
            turns.append({"gauge_id": gauge["id"], "kind": "high", "time_min": rows[i]["time_min"], "level_m": fmt(level)})
        if prev_level - level >= delta and next_level - level >= delta:
            turns.append({"gauge_id": gauge["id"], "kind": "low", "time_min": rows[i]["time_min"], "level_m": fmt(level)})
    return turns


def sample_is_safe(model, gauge, row):
    """Return whether a sampled row can belong to a safe operating window."""
    flood, low = thresholds(model, gauge, row["time_min"])
    _, _, _, draft_shift = calibration_shifts(model, gauge, row["time_min"])
    draft = gauge["draft_m"] + draft_shift
    level = row["level"]
    ops = model["operations"]
    closed = any(
        c["gauge_id"] == gauge["id"] and c["start_min"] <= row["time_min"] <= c["end_min"]
        for c in model.get("closures", [])
    )
    blacked_out = any(
        b["segment"] == gauge["segment"] and b["start_min"] <= row["time_min"] <= b["end_min"]
        for b in model.get("blackouts", [])
    )
    return (
        not closed
        and not blacked_out
        and level < flood
        and level > low
        and level >= draft + ops["min_under_keel_m"]
        and level <= flood - ops["flood_buffer_m"]
    )


def slope_per_hour(a, b):
    """Compute the signed slope between adjacent samples in meters per hour."""
    return (b["level"] - a["level"]) / ((b["time_min"] - a["time_min"]) / 60.0)


def window_from_run(model, gauge, run):
    """Convert one safe run into an internal window with unrounded metrics."""
    slopes = [abs(slope_per_hour(run[i], run[i + 1])) for i in range(len(run) - 1)]
    return {
        "gauge_id": gauge["id"],
        "segment": gauge["segment"],
        "start_min": run[0]["time_min"],
        "end_min": run[-1]["time_min"],
        "min_clearance_value": min(row["level"] - gauge["draft_m"] - calibration_shifts(model, gauge, row["time_min"])[3] for row in run),
        "max_abs_slope_value": max(slopes) if slopes else 0.0,
        "target_error_value": sum(abs(row["level"] - model["operations"]["target_level_m"]) for row in run) / len(run),
    }


def publish_window(window):
    """Convert an internal window into the exact JSON-facing window schema."""
    return {
        "gauge_id": window["gauge_id"],
        "segment": window["segment"],
        "start_min": window["start_min"],
        "end_min": window["end_min"],
        "min_clearance_m": fmt(window["min_clearance_value"]),
        "max_abs_slope_m_per_hour": fmt(window["max_abs_slope_value"]),
        "target_error_m": fmt(window["target_error_value"]),
    }


def build_windows(model, gauge, rows):
    """Build maximal safe windows while enforcing adjacent slope limits."""
    ops = model["operations"]
    windows = []
    i = 0
    while i < len(rows):
        if not sample_is_safe(model, gauge, rows[i]):
            i += 1
            continue
        run = [rows[i]]
        i += 1
        while i < len(rows) and sample_is_safe(model, gauge, rows[i]):
            slope = abs(slope_per_hour(run[-1], rows[i]))
            if slope > ops["max_slope_m_per_hour"]:
                break
            run.append(rows[i])
            i += 1
        if run[-1]["time_min"] - run[0]["time_min"] >= ops["min_window_min"]:
            windows.append(window_from_run(model, gauge, run))
    return windows


def select_windows(windows, gauges):
    """Select the best window per segment using the required tie-break chain."""
    priority = {g["id"]: g["priority"] for g in gauges}
    best_by_segment = {}
    for window in windows:
        current = best_by_segment.get(window["segment"])
        if current is None or selection_key(window, priority) < selection_key(current, priority):
            best_by_segment[window["segment"]] = window
    return [best_by_segment[seg] for seg in sorted(best_by_segment)]


def selection_key(window, priority):
    """Return the sortable key for selected-window precedence."""
    return (
        -priority[window["gauge_id"]],
        window["target_error_value"],
        -(window["end_min"] - window["start_min"]),
        window["max_abs_slope_value"],
        window["start_min"],
        window["gauge_id"],
    )


def publish_route_plan(route, plan, priority):
    """Convert one internal route plan into the exact JSON-facing schema."""
    total_priority = sum(priority[w["gauge_id"]] for w in plan)
    total_duration = sum(w["end_min"] - w["start_min"] for w in plan)
    layovers = [plan[i]["start_min"] - plan[i - 1]["end_min"] for i in range(1, len(plan))]
    handoff_penalty = route_handoff_penalty(route, plan)
    total_target_error = sum(w["target_error_value"] for w in plan) + handoff_penalty
    max_slope = max((w["max_abs_slope_value"] for w in plan), default=0.0)
    return {
        "route_id": route["id"],
        "segments": list(route["segments"]),
        "windows": [publish_window(w) for w in plan],
        "layovers_min": layovers,
        "total_priority": total_priority,
        "total_duration_min": total_duration,
        "total_target_error_m": fmt(total_target_error),
        "total_handoff_penalty_m": fmt(handoff_penalty),
        "max_abs_slope_m_per_hour": fmt(max_slope),
    }


def route_handoff_penalty(route, plan):
    """Return the configured route penalty for changing gauges between adjacent legs."""
    if not plan:
        return 0.0
    penalty = route.get("handoff_penalty_m")
    if penalty is None:
        penalty = route.get("_operations_handoff_penalty_m", 0.0)
    return sum(penalty for i in range(1, len(plan)) if plan[i]["gauge_id"] != plan[i - 1]["gauge_id"])


def route_key(route, plan, priority):
    """Return the sortable key for complete-route precedence."""
    return (
        -sum(priority[w["gauge_id"]] for w in plan),
        sum(w["target_error_value"] for w in plan) + route_handoff_penalty(route, plan),
        -sum(w["end_min"] - w["start_min"] for w in plan),
        max((w["max_abs_slope_value"] for w in plan), default=0.0),
        plan[0]["start_min"] if plan else 0,
        ",".join(w["gauge_id"] for w in plan),
    )


def segment_crew_cost(model, segment_id):
    """Return the integer crew cost configured for a route segment."""
    for segment in model.get("segments", []):
        if segment["id"] == segment_id:
            return segment.get("crew_cost", 0)
    return 0


def route_capacity_allows(model, route, plan, gauge_capacity):
    """Return whether each selected gauge has enough cumulative crew capacity."""
    used = {}
    for segment_id, window in zip(route["segments"], plan):
        cost = segment_crew_cost(model, segment_id)
        if cost == 0:
            continue
        gauge_id = window["gauge_id"]
        used[gauge_id] = used.get(gauge_id, 0) + cost
        if used[gauge_id] > gauge_capacity.get(gauge_id, 0):
            return False
    return True


def checkpoint_allows(route, index, window):
    """Return whether the candidate window satisfies every checkpoint for this route index."""
    for checkpoint in route.get("checkpoints", []):
        if checkpoint["index"] != index:
            continue
        if window["start_min"] < checkpoint["earliest_start_min"]:
            return False
        if window["end_min"] > checkpoint["latest_end_min"]:
            return False
        required = checkpoint.get("required_gauge_id", "")
        if required and window["gauge_id"] != required:
            return False
    return True


def transition_allowed(route, previous, current):
    """Return whether an adjacent route transition avoids every forbidden pattern."""
    for transition in route.get("forbidden_transitions", []):
        from_id = transition.get("from_gauge_id", "")
        to_id = transition.get("to_gauge_id", "")
        from_matches = not from_id or previous["gauge_id"] == from_id
        to_matches = not to_id or current["gauge_id"] == to_id
        if from_matches and to_matches:
            return False
    return True


def best_route_plan(model, route, windows, gauges, ops):
    """Choose the best complete compatible route plan, if one exists."""
    priority = {g["id"]: g["priority"] for g in gauges}
    gauge_capacity = {g["id"]: g.get("crew_capacity", 0) for g in gauges}
    route = copy.deepcopy(route)
    route["_operations_handoff_penalty_m"] = ops.get("route_handoff_penalty_m", 0.0)
    by_segment = {}
    for window in windows:
        by_segment.setdefault(window["segment"], []).append(window)
    for candidates in by_segment.values():
        candidates.sort(key=lambda w: (w["start_min"], w["end_min"], w["gauge_id"]))

    best = None

    def visit(index, plan):
        nonlocal best
        if index == len(route["segments"]):
            if not route_capacity_allows(model, route, plan, gauge_capacity):
                return
            max_error = ops.get("route_max_total_target_error_m")
            if max_error is not None and route_key(route, plan, priority)[1] > max_error:
                return
            if best is None or route_key(route, plan, priority) < route_key(route, best, priority):
                best = list(plan)
            return
        segment = route["segments"][index]
        for window in by_segment.get(segment, []):
            if not checkpoint_allows(route, index, window):
                continue
            if ops.get("route_no_repeat_gauge", False) and any(w["gauge_id"] == window["gauge_id"] for w in plan):
                continue
            if plan:
                if not transition_allowed(route, plan[-1], window):
                    continue
                gap = window["start_min"] - plan[-1]["end_min"]
                if gap < ops["route_min_gap_min"] or gap > ops["route_max_layover_min"]:
                    continue
            plan.append(window)
            visit(index + 1, plan)
            plan.pop()

    visit(0, [])
    if best is None:
        return None
    return publish_route_plan(route, best, priority)


def build_route_plans(model, windows, gauges):
    """Build expected route plans for every complete route request."""
    plans = []
    for route in model.get("routes", []):
        plan = best_route_plan(model, route, windows, gauges, model["operations"])
        if plan is not None:
            plans.append(plan)
    plans.sort(key=lambda x: x["route_id"])
    return plans


def expected_report(model, gauges):
    """Build the complete expected report for a generated model and gauges."""
    samples = []
    alerts = []
    turns = []
    windows = []
    for gauge in gauges:
        rows = []
        for t in range(model["start_min"], model["end_min"] + 1, model["step_min"]):
            level = level_at(model, gauge, t)
            rows.append({"time_min": t, "level": level})
            samples.append({"gauge_id": gauge["id"], "time_min": t, "level_m": fmt(level)})
        alerts.extend(build_alerts(model, gauge, rows, "flood"))
        alerts.extend(build_alerts(model, gauge, rows, "low"))
        turns.extend(build_turns(model, gauge, rows))
        windows.extend(build_windows(model, gauge, rows))
    selected = select_windows(windows, gauges)
    route_plans = build_route_plans(model, windows, gauges)
    samples.sort(key=lambda x: (x["gauge_id"], x["time_min"]))
    alerts.sort(key=lambda x: (x["gauge_id"], x["start_min"], x["kind"]))
    turns.sort(key=lambda x: (x["gauge_id"], x["time_min"], x["kind"]))
    windows.sort(key=lambda x: (x["segment"], x["start_min"], x["gauge_id"]))
    return {
        "samples": samples,
        "alerts": alerts,
        "turns": turns,
        "windows": [publish_window(w) for w in windows],
        "selected_windows": [publish_window(w) for w in selected],
        "route_plans": route_plans,
        "summary": {
            "gauge_count": len(gauges),
            "sample_count": len(samples),
            "flood_alerts": sum(1 for a in alerts if a["kind"] == "flood"),
            "low_alerts": sum(1 for a in alerts if a["kind"] == "low"),
            "turn_count": len(turns),
            "window_count": len(windows),
            "selected_window_count": len(selected),
            "route_plan_count": len(route_plans),
        },
    }


def assert_case(model, gauges):
    """Compare candidate output against the reference report for one case."""
    assert run_case(model, gauges) == expected_report(model, gauges)


def test_visible_input_files_are_unchanged():
    """Ensure the bundled model and gauge fixtures remain unchanged by the solution."""
    assert (APP / "model.json").read_text() == ORIGINAL_MODEL
    assert (APP / "gauges.jsonl").read_text() == ORIGINAL_GAUGES


def test_public_fixture_uses_phase_drift_segments_alerts_turns_and_windows():
    """Verify the public fixture exercises harmonic phase, drift, segment thresholds, alerts, turns, and windows."""
    assert_case(base_model(), base_gauges())


def test_tie_extreme_turn_delta_and_fallback_thresholds():
    """Check fallback thresholds, inclusive turn deltas, and earliest extreme selection on ties."""
    model = {
        "start_min": 0,
        "end_min": 180,
        "step_min": 60,
        "datum_m": 1.0,
        "flood_threshold_m": 1.5,
        "low_threshold_m": 0.5,
        "turn_min_delta_m": 0.5,
        "constituents": [
            {"name": "flat", "amplitude_m": 0.5, "speed_deg_per_hour": 0.0, "phase_deg": 0.0, "nodal_factor": 1.0, "epoch_min": 0}
        ],
        "segments": [],
        "closures": [],
        "operations": {
            "min_under_keel_m": 0.2,
            "flood_buffer_m": 0.0,
            "max_slope_m_per_hour": 0.5,
            "min_window_min": 180,
            "target_level_m": 1.5,
            "route_handoff_penalty_m": 0.0,
            "route_min_gap_min": 0,
            "route_max_layover_min": 180,
            "route_no_repeat_gauge": False,
        },
        "routes": [],
    }
    gauges = [{"id": "g", "segment": "missing", "offset_m": 0.0, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.6, "priority": 1}]
    assert_case(model, gauges)


def test_low_alerts_final_sample_inclusive_and_slope_breaks_windows():
    """Verify low-alert intervals include final samples and slope breaks split candidate safe windows."""
    model = copy.deepcopy(base_model())
    model["start_min"] = 30
    model["end_min"] = 390
    model["step_min"] = 45
    model["datum_m"] = 0.95
    model["low_threshold_m"] = 0.72
    model["operations"]["max_slope_m_per_hour"] = 0.42
    model["operations"]["min_window_min"] = 90
    model["closures"] = []
    gauges = [
        {"id": "lagged", "segment": "unknown", "offset_m": -0.08, "scale": 1.08, "drift_m_per_day": -0.03, "phase_lag_min": 37, "draft_m": 0.36, "priority": 5}
    ]
    assert_case(model, gauges)


def test_selected_window_tie_breaks_after_priority():
    """Check selected-window tie-break order after equal priority using target error and later criteria."""
    model = {
        "start_min": 0,
        "end_min": 240,
        "step_min": 60,
        "datum_m": 1.4,
        "flood_threshold_m": 3.0,
        "low_threshold_m": 0.0,
        "turn_min_delta_m": 0.1,
        "constituents": [
            {"name": "slow", "amplitude_m": 0.16, "speed_deg_per_hour": 45.0, "phase_deg": 0.0, "nodal_factor": 1.0, "epoch_min": 0}
        ],
        "segments": [{"id": "pier", "flood_threshold_m": 3.0, "low_threshold_m": 0.0}],
        "closures": [],
        "operations": {
            "min_under_keel_m": 0.15,
            "flood_buffer_m": 0.2,
            "max_slope_m_per_hour": 0.2,
            "min_window_min": 120,
            "target_level_m": 1.45,
            "route_min_gap_min": 0,
            "route_max_layover_min": 240,
            "route_no_repeat_gauge": False,
        },
        "routes": [{"id": "pier-hop", "segments": ["pier"]}],
    }
    gauges = [
        {"id": "alpha", "segment": "pier", "offset_m": 0.00, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.8, "priority": 2},
        {"id": "bravo", "segment": "pier", "offset_m": 0.04, "scale": 0.7, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.8, "priority": 2},
        {"id": "charlie", "segment": "pier", "offset_m": -0.02, "scale": 1.2, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.8, "priority": 1},
    ]
    assert_case(model, gauges)


def test_route_plan_requires_complete_global_choice():
    """Check that route selection compares complete compatible plans, not local segment winners."""
    model = {
        "start_min": 0,
        "end_min": 540,
        "step_min": 60,
        "datum_m": 0.0,
        "flood_threshold_m": 3.0,
        "low_threshold_m": 0.0,
        "turn_min_delta_m": 0.2,
        "constituents": [],
        "segments": [
            {"id": "alpha", "flood_threshold_m": 3.0, "low_threshold_m": 0.0},
            {"id": "bravo", "flood_threshold_m": 3.0, "low_threshold_m": 0.0},
            {"id": "charlie", "flood_threshold_m": 3.0, "low_threshold_m": 0.0},
        ],
        "closures": [
            {"gauge_id": "alpha-late-high", "start_min": 360, "end_min": 420}
        ],
        "operations": {
            "min_under_keel_m": 0.3,
            "flood_buffer_m": 1.0,
            "max_slope_m_per_hour": 1.0,
            "min_window_min": 60,
            "target_level_m": 1.50,
            "route_min_gap_min": 60,
            "route_max_layover_min": 120,
            "route_no_repeat_gauge": True,
        },
        "routes": [{"id": "three-hop", "segments": ["alpha", "bravo", "charlie"]}],
    }
    gauges = [
        {"id": "alpha-late-high", "segment": "alpha", "offset_m": -2.0, "scale": 1.0, "drift_m_per_day": 24.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 9},
        {"id": "alpha-early", "segment": "alpha", "offset_m": 1.0, "scale": 1.0, "drift_m_per_day": 24.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 4},
        {"id": "bravo-mid", "segment": "bravo", "offset_m": -2.0, "scale": 1.0, "drift_m_per_day": 24.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 5},
        {"id": "charlie-end", "segment": "charlie", "offset_m": -5.0, "scale": 1.0, "drift_m_per_day": 24.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 5},
    ]
    assert_case(model, gauges)


def test_closures_split_windows_but_not_samples_alerts_or_turns():
    """Check inclusive closure endpoints and that closure rules affect only planning windows."""
    model = {
        "start_min": 0,
        "end_min": 360,
        "step_min": 60,
        "datum_m": 1.2,
        "flood_threshold_m": 2.4,
        "low_threshold_m": 0.2,
        "turn_min_delta_m": 0.05,
        "constituents": [
            {"name": "pulse", "amplitude_m": 0.35, "speed_deg_per_hour": 30.0, "phase_deg": 0.0, "nodal_factor": 1.0, "epoch_min": 0}
        ],
        "segments": [{"id": "dock", "flood_threshold_m": 2.4, "low_threshold_m": 0.2}],
        "closures": [{"gauge_id": "dock-a", "start_min": 120, "end_min": 180}],
        "operations": {
            "min_under_keel_m": 0.2,
            "flood_buffer_m": 0.1,
            "max_slope_m_per_hour": 0.3,
            "min_window_min": 60,
            "target_level_m": 1.2,
            "route_min_gap_min": 0,
            "route_max_layover_min": 240,
            "route_no_repeat_gauge": True,
        },
        "routes": [{"id": "dock-repeat", "segments": ["dock", "dock"]}],
    }
    gauges = [
        {"id": "dock-a", "segment": "dock", "offset_m": 0.0, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 5},
        {"id": "dock-b", "segment": "dock", "offset_m": 0.1, "scale": 0.7, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 1},
    ]
    assert_case(model, gauges)


def test_route_repeat_gauge_flag_changes_feasibility():
    """Verify repeated use of one gauge is allowed only when the route flag permits it."""
    model = {
        "start_min": 0,
        "end_min": 300,
        "step_min": 60,
        "datum_m": 1.2,
        "flood_threshold_m": 2.8,
        "low_threshold_m": 0.2,
        "turn_min_delta_m": 0.1,
        "constituents": [],
        "segments": [{"id": "dock", "flood_threshold_m": 2.8, "low_threshold_m": 0.2}],
        "closures": [{"gauge_id": "dock-main", "start_min": 120, "end_min": 120}],
        "operations": {
            "min_under_keel_m": 0.2,
            "flood_buffer_m": 0.2,
            "max_slope_m_per_hour": 0.2,
            "min_window_min": 60,
            "target_level_m": 1.2,
            "route_min_gap_min": 60,
            "route_max_layover_min": 180,
            "route_no_repeat_gauge": False,
        },
        "routes": [{"id": "repeat-service", "segments": ["dock", "dock"]}],
    }
    gauges = [{"id": "dock-main", "segment": "dock", "offset_m": 0.0, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 8}]
    assert_case(model, gauges)

    no_repeat_model = copy.deepcopy(model)
    no_repeat_model["operations"]["route_no_repeat_gauge"] = True
    assert_case(no_repeat_model, gauges)


def test_route_tie_break_compares_complete_gauge_sequence():
    """Verify route ties are resolved by the complete chosen gauge-id sequence."""
    model = {
        "start_min": 0,
        "end_min": 300,
        "step_min": 60,
        "datum_m": 1.4,
        "flood_threshold_m": 3.0,
        "low_threshold_m": 0.0,
        "turn_min_delta_m": 0.2,
        "constituents": [],
        "segments": [
            {"id": "alpha", "flood_threshold_m": 3.0, "low_threshold_m": 0.0},
            {"id": "bravo", "flood_threshold_m": 3.0, "low_threshold_m": 0.0},
        ],
        "closures": [],
        "operations": {
            "min_under_keel_m": 0.2,
            "flood_buffer_m": 0.2,
            "max_slope_m_per_hour": 0.2,
            "min_window_min": 60,
            "target_level_m": 1.4,
            "route_min_gap_min": 0,
            "route_max_layover_min": 300,
            "route_no_repeat_gauge": True,
        },
        "routes": [{"id": "lex-route", "segments": ["alpha", "bravo"]}],
    }
    gauges = [
        {"id": "alpha-a", "segment": "alpha", "offset_m": 0.0, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 4},
        {"id": "alpha-b", "segment": "alpha", "offset_m": 0.0, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 4},
        {"id": "bravo-a", "segment": "bravo", "offset_m": 0.0, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 4},
        {"id": "bravo-b", "segment": "bravo", "offset_m": 0.0, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 4},
    ]
    assert_case(model, gauges)


def test_blackouts_checkpoints_layovers_and_handoff_penalty():
    """Verify segment blackouts split windows and route checkpoints/handoff penalties affect global choice."""
    model = {
        "start_min": 0,
        "end_min": 420,
        "step_min": 60,
        "datum_m": 1.3,
        "flood_threshold_m": 3.0,
        "low_threshold_m": 0.0,
        "turn_min_delta_m": 0.2,
        "constituents": [],
        "segments": [
            {"id": "alpha", "flood_threshold_m": 3.0, "low_threshold_m": 0.0},
            {"id": "bravo", "flood_threshold_m": 3.0, "low_threshold_m": 0.0},
            {"id": "charlie", "flood_threshold_m": 3.0, "low_threshold_m": 0.0},
        ],
        "closures": [],
        "blackouts": [
            {"segment": "alpha", "start_min": 120, "end_min": 120},
            {"segment": "bravo", "start_min": 0, "end_min": 180},
        ],
        "operations": {
            "min_under_keel_m": 0.2,
            "flood_buffer_m": 0.2,
            "max_slope_m_per_hour": 0.2,
            "min_window_min": 60,
            "target_level_m": 1.3,
            "route_handoff_penalty_m": 0.35,
            "route_min_gap_min": 0,
            "route_max_layover_min": 180,
            "route_no_repeat_gauge": False,
        },
        "routes": [
            {
                "id": "checkpointed",
                "segments": ["alpha", "bravo", "charlie"],
                "checkpoints": [
                    {"index": 0, "earliest_start_min": 180, "latest_end_min": 420, "required_gauge_id": ""},
                    {"index": 1, "earliest_start_min": 240, "latest_end_min": 420, "required_gauge_id": "bravo-main"},
                    {"index": 2, "earliest_start_min": 300, "latest_end_min": 420, "required_gauge_id": ""},
                ],
            }
        ],
    }
    gauges = [
        {"id": "alpha-main", "segment": "alpha", "offset_m": 0.00, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 4},
        {"id": "alpha-alt", "segment": "alpha", "offset_m": 0.06, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 5},
        {"id": "bravo-main", "segment": "bravo", "offset_m": 0.02, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 5},
        {"id": "bravo-wrong", "segment": "bravo", "offset_m": 0.00, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 9},
        {"id": "charlie-main", "segment": "charlie", "offset_m": 0.04, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 4},
    ]
    assert_case(model, gauges)


def test_route_specific_handoff_penalty_overrides_operations_default():
    """Verify a route-level handoff penalty can change the complete winning plan."""
    model = {
        "start_min": 0,
        "end_min": 420,
        "step_min": 60,
        "datum_m": 1.3,
        "flood_threshold_m": 3.0,
        "low_threshold_m": 0.0,
        "turn_min_delta_m": 0.2,
        "constituents": [],
        "segments": [{"id": "dock", "flood_threshold_m": 3.0, "low_threshold_m": 0.0}],
        "closures": [
            {"gauge_id": "alpha", "start_min": 120, "end_min": 120},
            {"gauge_id": "bravo", "start_min": 0, "end_min": 120},
        ],
        "operations": {
            "min_under_keel_m": 0.2,
            "flood_buffer_m": 0.2,
            "max_slope_m_per_hour": 0.2,
            "min_window_min": 60,
            "target_level_m": 1.3,
            "route_handoff_penalty_m": 0.0,
            "route_min_gap_min": 60,
            "route_max_layover_min": 180,
            "route_no_repeat_gauge": False,
        },
        "routes": [
            {
                "id": "override-hop",
                "segments": ["dock", "dock"],
                "handoff_penalty_m": 0.20,
                "checkpoints": [
                    {"index": 0, "earliest_start_min": 0, "latest_end_min": 60, "required_gauge_id": "alpha"},
                    {"index": 1, "earliest_start_min": 180, "latest_end_min": 420, "required_gauge_id": ""},
                ],
            }
        ],
    }
    gauges = [
        {"id": "alpha", "segment": "dock", "offset_m": 0.05, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 5},
        {"id": "bravo", "segment": "dock", "offset_m": 0.00, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 5},
    ]
    assert_case(model, gauges)


def test_calibration_events_shift_levels_thresholds_drafts_and_alerts():
    """Verify overlapping calibration events affect samples, alert thresholds, and safe-window clearance."""
    model = {
        "start_min": 0,
        "end_min": 300,
        "step_min": 60,
        "datum_m": 1.2,
        "flood_threshold_m": 1.75,
        "low_threshold_m": 0.65,
        "turn_min_delta_m": 0.05,
        "constituents": [
            {"name": "swing", "amplitude_m": 0.25, "speed_deg_per_hour": 60.0, "phase_deg": 0.0, "nodal_factor": 1.0, "epoch_min": 0}
        ],
        "segments": [{"id": "inner", "flood_threshold_m": 1.62, "low_threshold_m": 0.72}],
        "calibration_events": [
            {"target": "*", "start_min": 60, "end_min": 180, "level_shift_m": 0.06, "flood_threshold_shift_m": 0.02, "low_threshold_shift_m": -0.01, "draft_shift_m": 0.02},
            {"target": "inner", "start_min": 120, "end_min": 240, "level_shift_m": -0.09, "flood_threshold_shift_m": -0.05, "low_threshold_shift_m": 0.04, "draft_shift_m": 0.05},
            {"target": "gauge-b", "start_min": 180, "end_min": 300, "level_shift_m": 0.04, "flood_threshold_shift_m": 0.00, "low_threshold_shift_m": 0.03, "draft_shift_m": -0.03},
        ],
        "closures": [{"gauge_id": "gauge-a", "start_min": 240, "end_min": 240}],
        "blackouts": [],
        "operations": {
            "min_under_keel_m": 0.28,
            "flood_buffer_m": 0.08,
            "max_slope_m_per_hour": 0.55,
            "min_window_min": 60,
            "target_level_m": 1.18,
            "route_handoff_penalty_m": 0.04,
            "route_min_gap_min": 0,
            "route_max_layover_min": 180,
            "route_no_repeat_gauge": False,
            "route_max_total_target_error_m": 1.1,
        },
        "routes": [{"id": "inner-hop", "segments": ["inner", "inner"], "forbidden_transitions": [{"from_gauge_id": "gauge-a", "to_gauge_id": "gauge-b"}]}],
    }
    gauges = [
        {"id": "gauge-a", "segment": "inner", "offset_m": 0.03, "scale": 1.0, "drift_m_per_day": 0.04, "phase_lag_min": 0, "draft_m": 0.74, "priority": 4},
        {"id": "gauge-b", "segment": "inner", "offset_m": -0.02, "scale": 0.85, "drift_m_per_day": -0.02, "phase_lag_min": 15, "draft_m": 0.70, "priority": 5},
    ]
    assert_case(model, gauges)


def test_route_error_cap_filters_before_priority_tiebreak():
    """Verify over-budget high-priority complete plans are discarded before selecting a route winner."""
    model = {
        "start_min": 0,
        "end_min": 420,
        "step_min": 60,
        "datum_m": 1.0,
        "flood_threshold_m": 3.0,
        "low_threshold_m": 0.0,
        "turn_min_delta_m": 0.1,
        "constituents": [],
        "segments": [
            {"id": "alpha", "flood_threshold_m": 3.0, "low_threshold_m": 0.0},
            {"id": "bravo", "flood_threshold_m": 3.0, "low_threshold_m": 0.0},
            {"id": "charlie", "flood_threshold_m": 3.0, "low_threshold_m": 0.0},
        ],
        "calibration_events": [
            {"target": "alpha-hi", "start_min": 0, "end_min": 420, "level_shift_m": 0.55, "flood_threshold_shift_m": 0.0, "low_threshold_shift_m": 0.0, "draft_shift_m": 0.0},
            {"target": "bravo-hi", "start_min": 0, "end_min": 420, "level_shift_m": 0.55, "flood_threshold_shift_m": 0.0, "low_threshold_shift_m": 0.0, "draft_shift_m": 0.0},
            {"target": "charlie-hi", "start_min": 0, "end_min": 420, "level_shift_m": 0.55, "flood_threshold_shift_m": 0.0, "low_threshold_shift_m": 0.0, "draft_shift_m": 0.0},
        ],
        "closures": [
            {"gauge_id": "alpha-hi", "start_min": 120, "end_min": 420},
            {"gauge_id": "bravo-hi", "start_min": 0, "end_min": 120},
            {"gauge_id": "charlie-hi", "start_min": 0, "end_min": 240},
        ],
        "blackouts": [],
        "operations": {
            "min_under_keel_m": 0.2,
            "flood_buffer_m": 0.2,
            "max_slope_m_per_hour": 0.2,
            "min_window_min": 60,
            "target_level_m": 1.0,
            "route_handoff_penalty_m": 0.02,
            "route_min_gap_min": 60,
            "route_max_layover_min": 180,
            "route_no_repeat_gauge": True,
            "route_max_total_target_error_m": 0.35,
        },
        "routes": [
            {
                "id": "budgeted-chain",
                "segments": ["alpha", "bravo", "charlie"],
                "forbidden_transitions": [
                    {"from_gauge_id": "alpha-low", "to_gauge_id": "bravo-low"},
                    {"from_gauge_id": "", "to_gauge_id": "charlie-blocked"},
                ],
            }
        ],
    }
    gauges = [
        {"id": "alpha-hi", "segment": "alpha", "offset_m": 0.0, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.65, "priority": 9},
        {"id": "alpha-low", "segment": "alpha", "offset_m": 0.02, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.65, "priority": 3},
        {"id": "bravo-hi", "segment": "bravo", "offset_m": 0.0, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.65, "priority": 9},
        {"id": "bravo-low", "segment": "bravo", "offset_m": 0.03, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.65, "priority": 3},
        {"id": "charlie-hi", "segment": "charlie", "offset_m": 0.0, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.65, "priority": 9},
        {"id": "charlie-low", "segment": "charlie", "offset_m": -0.01, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.65, "priority": 3},
        {"id": "charlie-blocked", "segment": "charlie", "offset_m": 0.0, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.65, "priority": 8},
    ]
    assert_case(model, gauges)


def test_route_crew_capacity_filters_complete_plans_before_priority():
    """Verify cumulative segment crew costs are checked per chosen gauge before route tie-breaks."""
    model = {
        "start_min": 0,
        "end_min": 420,
        "step_min": 60,
        "datum_m": 1.3,
        "flood_threshold_m": 3.0,
        "low_threshold_m": 0.0,
        "turn_min_delta_m": 0.2,
        "constituents": [],
        "segments": [
            {"id": "alpha", "flood_threshold_m": 3.0, "low_threshold_m": 0.0, "crew_cost": 2},
            {"id": "bravo", "flood_threshold_m": 3.0, "low_threshold_m": 0.0, "crew_cost": 2},
            {"id": "charlie", "flood_threshold_m": 3.0, "low_threshold_m": 0.0, "crew_cost": 1},
        ],
        "closures": [
            {"gauge_id": "alpha-hi", "start_min": 120, "end_min": 120},
            {"gauge_id": "bravo-hi", "start_min": 0, "end_min": 120},
            {"gauge_id": "bravo-hi", "start_min": 300, "end_min": 420},
            {"gauge_id": "alpha-only", "start_min": 180, "end_min": 420},
            {"gauge_id": "bravo-safe", "start_min": 0, "end_min": 120},
            {"gauge_id": "bravo-safe", "start_min": 300, "end_min": 420},
            {"gauge_id": "charlie-safe", "start_min": 0, "end_min": 240},
        ],
        "blackouts": [],
        "operations": {
            "min_under_keel_m": 0.2,
            "flood_buffer_m": 0.2,
            "max_slope_m_per_hour": 0.2,
            "min_window_min": 60,
            "target_level_m": 1.3,
            "route_handoff_penalty_m": 0.03,
            "route_min_gap_min": 60,
            "route_max_layover_min": 180,
            "route_no_repeat_gauge": False,
        },
        "routes": [
            {
                "id": "capacity-chain",
                "segments": ["alpha", "bravo", "charlie"],
                "checkpoints": [
                    {"index": 0, "earliest_start_min": 0, "latest_end_min": 180, "required_gauge_id": ""},
                    {"index": 1, "earliest_start_min": 180, "latest_end_min": 240, "required_gauge_id": ""},
                    {"index": 2, "earliest_start_min": 300, "latest_end_min": 420, "required_gauge_id": ""},
                ],
            }
        ],
    }
    gauges = [
        {"id": "alpha-hi", "segment": "alpha", "offset_m": 0.04, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 10, "crew_capacity": 1},
        {"id": "bravo-hi", "segment": "bravo", "offset_m": 0.04, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 10, "crew_capacity": 1},
        {"id": "alpha-only", "segment": "alpha", "offset_m": 0.00, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 5, "crew_capacity": 2},
        {"id": "bravo-safe", "segment": "bravo", "offset_m": 0.02, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 5, "crew_capacity": 2},
        {"id": "charlie-safe", "segment": "charlie", "offset_m": -0.01, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 5, "crew_capacity": 1},
    ]
    assert_case(model, gauges)


def test_route_repeated_gauge_crew_capacity_accumulates():
    """Verify a repeated gauge can be allowed by repeat rules but rejected by cumulative crew use."""
    model = {
        "start_min": 0,
        "end_min": 360,
        "step_min": 60,
        "datum_m": 1.4,
        "flood_threshold_m": 3.0,
        "low_threshold_m": 0.0,
        "turn_min_delta_m": 0.2,
        "constituents": [],
        "segments": [{"id": "dock", "flood_threshold_m": 3.0, "low_threshold_m": 0.0, "crew_cost": 2}],
        "closures": [
            {"gauge_id": "dock-hi", "start_min": 120, "end_min": 120},
            {"gauge_id": "dock-alt", "start_min": 0, "end_min": 120},
        ],
        "blackouts": [],
        "operations": {
            "min_under_keel_m": 0.2,
            "flood_buffer_m": 0.2,
            "max_slope_m_per_hour": 0.2,
            "min_window_min": 60,
            "target_level_m": 1.4,
            "route_handoff_penalty_m": 0.01,
            "route_min_gap_min": 60,
            "route_max_layover_min": 180,
            "route_no_repeat_gauge": False,
        },
        "routes": [{"id": "repeat-capacity", "segments": ["dock", "dock"]}],
    }
    gauges = [
        {"id": "dock-hi", "segment": "dock", "offset_m": 0.02, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 9, "crew_capacity": 3},
        {"id": "dock-alt", "segment": "dock", "offset_m": -0.01, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.7, "priority": 4, "crew_capacity": 2},
    ]
    assert_case(model, gauges)


def test_epoch_nodal_drift_precision_and_boundary_windows():
    """Verify epoch offsets, nodal factors, drift, precision, and boundary-length windows."""
    model = {
        "start_min": -30,
        "end_min": 210,
        "step_min": 30,
        "datum_m": 1.1,
        "flood_threshold_m": 2.6,
        "low_threshold_m": -0.1,
        "turn_min_delta_m": 0.02,
        "constituents": [
            {"name": "q1", "amplitude_m": 0.173, "speed_deg_per_hour": 13.3986609, "phase_deg": 33.25, "nodal_factor": 1.037, "epoch_min": -75},
            {"name": "m4", "amplitude_m": 0.047, "speed_deg_per_hour": 57.9682084, "phase_deg": 181.4, "nodal_factor": 0.982, "epoch_min": 45},
        ],
        "segments": [{"id": "basin", "flood_threshold_m": 2.0, "low_threshold_m": 0.2}],
        "closures": [{"gauge_id": "basin-a", "start_min": 210, "end_min": 210}],
        "operations": {
            "min_under_keel_m": 0.15,
            "flood_buffer_m": 0.05,
            "max_slope_m_per_hour": 0.5,
            "min_window_min": 120,
            "target_level_m": 1.05,
            "route_min_gap_min": 0,
            "route_max_layover_min": 120,
            "route_no_repeat_gauge": False,
        },
        "routes": [{"id": "single", "segments": ["basin"]}],
    }
    gauges = [{"id": "basin-a", "segment": "basin", "offset_m": 0.017, "scale": 1.013, "drift_m_per_day": 0.021, "phase_lag_min": -11, "draft_m": 0.55, "priority": 6}]
    assert_case(model, gauges)


def test_generated_compatibility_matrix():
    """Exercise varied timing, thresholds, operations, phases, and segment fallback combinations."""
    for idx in range(20):
        model = copy.deepcopy(base_model())
        model["start_min"] = idx % 3 * 15
        model["end_min"] = model["start_min"] + 480 + (idx % 4) * 60
        model["step_min"] = 30 if idx % 2 else 60
        model["datum_m"] += (idx % 5 - 2) * 0.04
        model["flood_threshold_m"] += (idx % 3 - 1) * 0.08
        model["low_threshold_m"] += (idx % 4 - 1) * 0.04
        model["turn_min_delta_m"] = 0.04 + 0.01 * (idx % 5)
        model["operations"]["min_under_keel_m"] = 0.34 + 0.02 * (idx % 4)
        model["operations"]["flood_buffer_m"] = 0.10 + 0.02 * (idx % 3)
        model["operations"]["max_slope_m_per_hour"] = 0.45 + 0.03 * (idx % 5)
        model["operations"]["min_window_min"] = 60 if idx % 4 == 0 else 120
        model["operations"]["target_level_m"] = 1.32 + 0.03 * (idx % 6)
        model["operations"]["route_handoff_penalty_m"] = 0.01 * (idx % 4)
        model["operations"]["route_min_gap_min"] = 0 if idx % 3 else 30
        model["operations"]["route_max_layover_min"] = 180 + 30 * (idx % 4)
        model["operations"]["route_no_repeat_gauge"] = idx % 2 == 0
        model["constituents"][0]["phase_deg"] += idx * 7.5
        model["constituents"][1]["nodal_factor"] = 0.90 + 0.02 * (idx % 5)
        for seg_i, segment in enumerate(model["segments"]):
            segment["crew_cost"] = 1 + ((idx + seg_i) % 2)
        model["segments"].append({"id": f"reef-{idx}", "flood_threshold_m": 2.05 + 0.03 * idx, "low_threshold_m": 0.62 - 0.01 * (idx % 4), "crew_cost": 1 + idx % 3})
        model["calibration_events"] = [
            {"target": "*", "start_min": model["start_min"] + 60, "end_min": model["start_min"] + 180, "level_shift_m": 0.01 * (idx % 5 - 2), "flood_threshold_shift_m": -0.01 * (idx % 3), "low_threshold_shift_m": 0.01 * (idx % 2), "draft_shift_m": 0.0},
            {"target": f"reef-{idx}", "start_min": model["start_min"] + 180, "end_min": model["start_min"] + 360, "level_shift_m": -0.02 + 0.004 * idx, "flood_threshold_shift_m": 0.02, "low_threshold_shift_m": -0.01, "draft_shift_m": 0.01 * (idx % 4)},
            {"target": f"c-{idx}", "start_min": model["start_min"] + 90, "end_min": model["start_min"] + 300, "level_shift_m": 0.03, "flood_threshold_shift_m": 0.0, "low_threshold_shift_m": 0.02, "draft_shift_m": -0.01},
        ]
        model["closures"] = [
            {"gauge_id": f"a-{idx}", "start_min": model["start_min"] + 120, "end_min": model["start_min"] + 120 + model["step_min"]},
        ]
        if idx % 3 == 1:
            model["closures"].append({"gauge_id": f"b-{idx}", "start_min": model["start_min"] + 240, "end_min": model["start_min"] + 300})
        model["routes"] = [
            {"id": f"maintenance-{idx}", "segments": ["harbor", f"reef-{idx}", "missing"], "handoff_penalty_m": 0.02 + 0.01 * (idx % 5), "forbidden_transitions": [{"from_gauge_id": f"a-{idx}", "to_gauge_id": f"b-{idx}"}]},
            {"id": f"return-{idx}", "segments": [f"reef-{idx}", "harbor"], "forbidden_transitions": [{"from_gauge_id": "", "to_gauge_id": f"a-{idx}"}]},
            {"id": f"repeat-{idx}", "segments": ["harbor", "harbor"], "forbidden_transitions": [{"from_gauge_id": f"a-{idx}", "to_gauge_id": f"a-{idx}"}]},
        ]
        gauges = [
            {"id": f"a-{idx}", "segment": "harbor", "offset_m": 0.04 * (idx % 3), "scale": 0.94 + 0.01 * idx, "drift_m_per_day": -0.02 + 0.004 * idx, "phase_lag_min": -15 + idx, "draft_m": 0.54 + 0.01 * (idx % 4), "priority": 1 + idx % 4, "crew_capacity": 2 + idx % 3},
            {"id": f"b-{idx}", "segment": f"reef-{idx}", "offset_m": -0.06, "scale": 1.08, "drift_m_per_day": 0.012, "phase_lag_min": 18 - idx % 6, "draft_m": 0.50 + 0.02 * (idx % 3), "priority": 5 - idx % 3, "crew_capacity": 1 + idx % 4},
            {"id": f"c-{idx}", "segment": "missing", "offset_m": 0.12, "scale": 0.87 + 0.02 * (idx % 3), "drift_m_per_day": 0.0, "phase_lag_min": 25, "draft_m": 0.44 + 0.01 * (idx % 5), "priority": 2, "crew_capacity": 1},
        ]
        assert_case(model, gauges)


def test_seeded_randomized_harmonic_cases_resist_fixture_memorization():
    """Run deterministic generated cases with varied epochs, event targets, and route constraints."""
    rng = random.Random(8675309)
    for idx in range(18):
        start = rng.choice([-90, -45, 0, 15, 30])
        step = rng.choice([15, 30, 45, 60])
        sample_count = rng.randint(9, 18)
        end = start + step * (sample_count - 1)
        segment_ids = [f"seg-{idx}-{n}" for n in range(3)]
        gauge_ids = [f"g{idx}-{n}" for n in range(6)]
        model = {
            "start_min": start,
            "end_min": end,
            "step_min": step,
            "datum_m": rng.uniform(1.05, 1.55),
            "flood_threshold_m": rng.uniform(2.10, 2.55),
            "low_threshold_m": rng.uniform(0.25, 0.55),
            "turn_min_delta_m": rng.uniform(0.025, 0.085),
            "constituents": [
                {
                    "name": f"c{n}",
                    "amplitude_m": rng.uniform(0.04, 0.55),
                    "speed_deg_per_hour": rng.choice([13.3986609, 15.0410686, 28.9841042, 30.0, 57.9682084]),
                    "phase_deg": rng.uniform(-25.0, 210.0),
                    "nodal_factor": rng.uniform(0.91, 1.08),
                    "epoch_min": rng.choice([-120, -45, 0, 75, 135]),
                }
                for n in range(4)
            ],
            "segments": [
                {"id": segment_ids[n], "flood_threshold_m": 2.05 + 0.12 * n + rng.uniform(-0.03, 0.05), "low_threshold_m": 0.25 + 0.09 * n, "crew_cost": rng.randint(1, 3)}
                for n in range(2)
            ],
            "calibration_events": [
                {
                    "target": rng.choice(["*", segment_ids[0], segment_ids[2], gauge_ids[3]]),
                    "start_min": start + step * rng.randint(0, max(1, sample_count // 3)),
                    "end_min": start + step * rng.randint(sample_count // 2, sample_count - 1),
                    "level_shift_m": rng.uniform(-0.08, 0.08),
                    "flood_threshold_shift_m": rng.uniform(-0.04, 0.04),
                    "low_threshold_shift_m": rng.uniform(-0.03, 0.04),
                    "draft_shift_m": rng.uniform(-0.025, 0.045),
                }
                for _ in range(4)
            ],
            "closures": [
                {"gauge_id": gauge_ids[1], "start_min": start + step * 2, "end_min": start + step * 3},
                {"gauge_id": gauge_ids[4], "start_min": end - step * 2, "end_min": end - step},
            ],
            "blackouts": [
                {"segment": segment_ids[2], "start_min": start + step, "end_min": start + step * 2}
            ],
            "operations": {
                "min_under_keel_m": rng.uniform(0.18, 0.42),
                "flood_buffer_m": rng.uniform(0.02, 0.18),
                "max_slope_m_per_hour": rng.uniform(0.22, 0.75),
                "min_window_min": step * rng.choice([1, 2, 3]),
                "target_level_m": rng.uniform(1.05, 1.65),
                "route_handoff_penalty_m": rng.uniform(0.0, 0.12),
                "route_min_gap_min": rng.choice([0, step]),
                "route_max_layover_min": step * rng.randint(2, 6),
                "route_no_repeat_gauge": rng.choice([True, False]),
                "route_max_total_target_error_m": rng.choice([None, rng.uniform(0.45, 2.4)]),
            },
            "routes": [
                {
                    "id": f"seeded-{idx}-chain",
                    "segments": [segment_ids[0], segment_ids[1], segment_ids[2]],
                    "checkpoints": [
                        {"index": 0, "earliest_start_min": start, "latest_end_min": end, "required_gauge_id": ""},
                        {"index": 2, "earliest_start_min": start + step, "latest_end_min": end, "required_gauge_id": ""},
                    ],
                    "forbidden_transitions": [
                        {"from_gauge_id": gauge_ids[0], "to_gauge_id": gauge_ids[2]},
                        {"from_gauge_id": "", "to_gauge_id": gauge_ids[5]},
                    ],
                },
                {
                    "id": f"seeded-{idx}-repeat",
                    "segments": [segment_ids[0], segment_ids[0]],
                    "handoff_penalty_m": rng.uniform(0.01, 0.20),
                    "forbidden_transitions": [{"from_gauge_id": gauge_ids[0], "to_gauge_id": gauge_ids[0]}],
                },
            ],
        }
        if model["operations"]["route_max_total_target_error_m"] is None:
            del model["operations"]["route_max_total_target_error_m"]
        gauges = [
            {
                "id": gauge_ids[n],
                "segment": segment_ids[n % 3],
                "offset_m": rng.uniform(-0.18, 0.20),
                "scale": rng.uniform(0.76, 1.16),
                "drift_m_per_day": rng.uniform(-0.055, 0.065),
                "phase_lag_min": rng.randint(-34, 41),
                "draft_m": rng.uniform(0.42, 0.77),
                "priority": rng.randint(1, 9),
                "crew_capacity": rng.randint(1, 5),
            }
            for n in range(6)
        ]
        assert_case(model, gauges)


def test_optional_empty_fields_and_unsatisfiable_routes_still_emit_arrays():
    """Verify sparse input without optional lists and impossible route plans still has exact array output."""
    model = {
        "start_min": 0,
        "end_min": 120,
        "step_min": 60,
        "datum_m": 0.40,
        "flood_threshold_m": 1.00,
        "low_threshold_m": 0.55,
        "turn_min_delta_m": 0.20,
        "constituents": [],
        "segments": [],
        "operations": {
            "min_under_keel_m": 0.40,
            "flood_buffer_m": 0.30,
            "max_slope_m_per_hour": 0.10,
            "min_window_min": 60,
            "target_level_m": 1.10,
            "route_min_gap_min": 0,
            "route_max_layover_min": 60,
            "route_no_repeat_gauge": True,
        },
        "routes": [{"id": "missing-segment", "segments": ["absent"]}],
    }
    gauges = [
        {"id": "dry", "segment": "shoal", "offset_m": 0.0, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.60, "priority": 1}
    ]
    report = run_case(model, gauges)
    assert report == expected_report(model, gauges)
    assert report["windows"] == []
    assert report["selected_windows"] == []
    assert report["route_plans"] == []


def test_route_budget_pressure_with_many_dependency_alternatives():
    """Exercise a wider route-choice matrix with budget filtering and wildcard transition conflicts."""
    model = {
        "start_min": 0,
        "end_min": 540,
        "step_min": 60,
        "datum_m": 1.25,
        "flood_threshold_m": 3.10,
        "low_threshold_m": 0.10,
        "turn_min_delta_m": 0.10,
        "constituents": [],
        "segments": [
            {"id": "alpha", "flood_threshold_m": 3.10, "low_threshold_m": 0.10},
            {"id": "bravo", "flood_threshold_m": 3.10, "low_threshold_m": 0.10},
            {"id": "charlie", "flood_threshold_m": 3.10, "low_threshold_m": 0.10},
            {"id": "delta", "flood_threshold_m": 3.10, "low_threshold_m": 0.10},
        ],
        "closures": [],
        "blackouts": [],
        "calibration_events": [],
        "operations": {
            "min_under_keel_m": 0.25,
            "flood_buffer_m": 0.30,
            "max_slope_m_per_hour": 0.30,
            "min_window_min": 60,
            "target_level_m": 1.25,
            "route_handoff_penalty_m": 0.06,
            "route_min_gap_min": 0,
            "route_max_layover_min": 540,
            "route_no_repeat_gauge": True,
            "route_max_total_target_error_m": 0.42,
        },
        "routes": [
            {
                "id": "wide-budget",
                "segments": ["alpha", "bravo", "charlie", "delta"],
                "checkpoints": [
                    {"index": 0, "earliest_start_min": 0, "latest_end_min": 540, "required_gauge_id": ""},
                    {"index": 1, "earliest_start_min": 0, "latest_end_min": 540, "required_gauge_id": ""},
                    {"index": 2, "earliest_start_min": 0, "latest_end_min": 540, "required_gauge_id": ""},
                    {"index": 3, "earliest_start_min": 0, "latest_end_min": 540, "required_gauge_id": ""},
                ],
                "forbidden_transitions": [
                    {"from_gauge_id": "alpha-hi", "to_gauge_id": ""},
                    {"from_gauge_id": "", "to_gauge_id": "delta-trap"},
                    {"from_gauge_id": "bravo-safe", "to_gauge_id": "charlie-trap"},
                ],
            }
        ],
    }
    gauges = [
        {"id": "alpha-hi", "segment": "alpha", "offset_m": 0.35, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.55, "priority": 9},
        {"id": "alpha-safe", "segment": "alpha", "offset_m": 0.02, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.55, "priority": 5},
        {"id": "bravo-hi", "segment": "bravo", "offset_m": -0.34, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.55, "priority": 9},
        {"id": "bravo-safe", "segment": "bravo", "offset_m": -0.03, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.55, "priority": 5},
        {"id": "charlie-hi", "segment": "charlie", "offset_m": 0.33, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.55, "priority": 9},
        {"id": "charlie-safe", "segment": "charlie", "offset_m": 0.04, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.55, "priority": 5},
        {"id": "charlie-trap", "segment": "charlie", "offset_m": 0.01, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.55, "priority": 7},
        {"id": "delta-hi", "segment": "delta", "offset_m": -0.36, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.55, "priority": 9},
        {"id": "delta-safe", "segment": "delta", "offset_m": -0.02, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.55, "priority": 5},
        {"id": "delta-trap", "segment": "delta", "offset_m": 0.00, "scale": 1.0, "drift_m_per_day": 0.0, "phase_lag_min": 0, "draft_m": 0.55, "priority": 8},
    ]
    assert_case(model, gauges)


def test_boundary_events_at_negative_times_and_fractional_steps():
    """Check inclusive boundaries when time origins are negative and samples use a non-hour step."""
    model = {
        "start_min": -75,
        "end_min": 150,
        "step_min": 45,
        "datum_m": 1.12,
        "flood_threshold_m": 1.78,
        "low_threshold_m": 0.52,
        "turn_min_delta_m": 0.035,
        "constituents": [
            {"name": "x", "amplitude_m": 0.22, "speed_deg_per_hour": 30.0, "phase_deg": 15.0, "nodal_factor": 1.03, "epoch_min": -30},
            {"name": "y", "amplitude_m": 0.11, "speed_deg_per_hour": 57.9682084, "phase_deg": 190.0, "nodal_factor": 0.94, "epoch_min": 60},
        ],
        "segments": [{"id": "basin", "flood_threshold_m": 1.70, "low_threshold_m": 0.47}],
        "calibration_events": [
            {"target": "*", "start_min": -75, "end_min": -30, "level_shift_m": 0.03, "flood_threshold_shift_m": -0.02, "low_threshold_shift_m": 0.01, "draft_shift_m": 0.02},
            {"target": "basin", "start_min": 15, "end_min": 150, "level_shift_m": -0.04, "flood_threshold_shift_m": 0.03, "low_threshold_shift_m": -0.02, "draft_shift_m": -0.01},
        ],
        "closures": [{"gauge_id": "basin-a", "start_min": -30, "end_min": -30}],
        "blackouts": [{"segment": "basin", "start_min": 105, "end_min": 150}],
        "operations": {
            "min_under_keel_m": 0.22,
            "flood_buffer_m": 0.04,
            "max_slope_m_per_hour": 0.62,
            "min_window_min": 45,
            "target_level_m": 1.08,
            "route_handoff_penalty_m": 0.03,
            "route_min_gap_min": 0,
            "route_max_layover_min": 180,
            "route_no_repeat_gauge": False,
        },
        "routes": [{"id": "basin-once", "segments": ["basin"]}],
    }
    gauges = [
        {"id": "basin-a", "segment": "basin", "offset_m": 0.04, "scale": 1.0, "drift_m_per_day": 0.032, "phase_lag_min": -17, "draft_m": 0.58, "priority": 4},
        {"id": "basin-b", "segment": "basin", "offset_m": -0.02, "scale": 0.92, "drift_m_per_day": -0.018, "phase_lag_min": 26, "draft_m": 0.54, "priority": 5},
    ]
    assert_case(model, gauges)
