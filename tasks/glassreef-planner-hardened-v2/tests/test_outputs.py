"""Verifier for the Glassreef submarine cable repair planner."""
import csv
import json
import os
import re
import shutil
import subprocess
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

APP = Path("/app")
OUTPUT = APP / "output" / "repair_plan.json"
TIME_FORMAT = "%Y-%m-%dT%H:%MZ"


def run_planner():
    env = os.environ.copy()
    env.setdefault("CARGO_TARGET_DIR", "/tmp/glassreef-target")
    result = subprocess.run(
        ["bash", "/app/scripts/run_glassreef_planner.sh"],
        cwd="/app",
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert OUTPUT.exists(), "planner did not create /app/output/repair_plan.json"
    return json.loads(OUTPUT.read_text()), OUTPUT.read_text()


def parse_time(value):
    return datetime.strptime(value, TIME_FORMAT).replace(tzinfo=timezone.utc)


def add_hours(value, hours):
    return (parse_time(value) + timedelta(hours=int(hours))).strftime(TIME_FORMAT)


def overlaps(a_start, a_end, b_start, b_end):
    return parse_time(a_start) < parse_time(b_end) and parse_time(b_start) < parse_time(a_end)


def read_csv_last_wins(path, key_fields):
    rows = []
    with open(path, newline="") as f:
        reader = csv.DictReader(row for row in f if row.strip() and not row.lstrip().startswith("#"))
        seen = {}
        order = []
        for row in reader:
            key = tuple(row[field].strip() for field in key_fields)
            cleaned = {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            if key not in seen:
                order.append(key)
            seen[key] = cleaned
    for key in order:
        rows.append(seen[key])
    return rows


def fnv1a64(text):
    h = 14695981039346656037
    for b in text.encode():
        h ^= b
        h = (h * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return f"{h:016x}"


def reachable(shores, edges):
    adj = defaultdict(list)
    for a, b in edges:
        adj[a].append(b)
        adj[b].append(a)
    seen = set(shores)
    q = deque(shores)
    while q:
        node = q.popleft()
        for nxt in adj[node]:
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return seen


def helper_drift_penalty(mean, bearing, depth):
    proc = subprocess.run(
        ["/app/build/current_adjust", f"{mean:.3f}", f"{bearing:.1f}", str(depth)],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return int(proc.stdout.strip())


def helper_duration_hours(length_nm):
    proc = subprocess.run(
        ["/app/build/repair_duration", f"{length_nm:.3f}"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=5,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return int(proc.stdout.strip())


def hazard_penalties():
    totals = defaultdict(int)
    hazard_dir = APP / "data/reference/hazards"
    for path in sorted(hazard_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text())
            region = str(payload["region"])
            severity = int(payload["severity"])
        except Exception:
            continue
        totals[region] += severity
    return {region: value // 100 for region, value in totals.items()}


def load_mission():
    payload = json.loads((APP / "data/missions/glassreef_primary.json").read_text())
    return {
        "cooldown": int(payload.get("ship_cooldown_hours", 0)),
        "blackouts": payload.get("ship_blackouts", []),
    }


def apply_station_profiles(stations):
    by_id = {row["station_id"]: dict(row) for row in stations}
    for path in sorted((APP / "data/network/station_profiles").glob("*.json")):
        try:
            payload = json.loads(path.read_text())
            station_id = str(payload["station_id"])
        except Exception:
            continue
        if station_id not in by_id:
            continue
        if "kind" in payload:
            by_id[station_id]["kind"] = str(payload["kind"])
        if "priority" in payload:
            by_id[station_id]["priority"] = str(int(payload["priority"]))
    return list(by_id.values())


def score(priority_base, restored_priority, compatibility_bonus, drift, depth, crew, hazard_penalty):
    crew_bonus = {"A": 8, "B": 4, "C": 1}.get(crew, 0)
    depth_penalty = 0 if depth <= 3000 else (depth - 3000) // 700
    return priority_base * 10 + restored_priority + compatibility_bonus + crew_bonus - drift - depth_penalty - hazard_penalty


def overlaps_blackout(ship_id, start, end, blackouts):
    for blackout in blackouts:
        if str(blackout.get("ship_id")) != ship_id:
            continue
        if overlaps(start, end, str(blackout.get("start_utc")), str(blackout.get("end_utc"))):
            return True
    return False


def can_schedule(candidate, intervals, cooldown_hours):
    start = candidate["start_utc"]
    end = candidate["end_utc"]
    for old_start, old_end in intervals:
        if overlaps(start, end, old_start, old_end):
            return False
        if parse_time(end) <= parse_time(old_start):
            if parse_time(add_hours(end, cooldown_hours)) > parse_time(old_start):
                return False
        elif parse_time(old_end) <= parse_time(start):
            if parse_time(add_hours(old_end, cooldown_hours)) > parse_time(start):
                return False
    return True


def expected_model():
    mission = load_mission()
    stations = apply_station_profiles(read_csv_last_wins(APP / "data/network/stations.csv", ("station_id",)))
    spans = read_csv_last_wins(APP / "data/network/spans.csv", ("span_id",))
    ships = read_csv_last_wins(APP / "data/vessels/ships.csv", ("ship_id",))
    windows = read_csv_last_wins(APP / "data/weather/windows.csv", ("window_id",))
    currents = read_csv_last_wins(APP / "data/currents/corridors.csv", ("corridor_id", "window_id"))
    rules = read_csv_last_wins(APP / "build/splice_rules.csv", ("family", "kit"))
    station_map = {s["station_id"]: s for s in stations}
    shores = sorted(s["station_id"] for s in stations if s["kind"] == "shore")
    ok_edges = [(s["from"], s["to"]) for s in spans if s["status"] == "OK"]
    base = reachable(shores, ok_edges)
    rule_map = defaultdict(dict)
    for row in rules:
        rule_map[row["family"]][row["kit"]] = int(row["bonus"])
    current_map = {(c["corridor_id"], c["window_id"]): c for c in currents}
    hazards = hazard_penalties()
    bundles = []
    for span in sorted([s for s in spans if s["status"] == "BROKEN"], key=lambda r: r["span_id"]):
        after = reachable(shores, ok_edges + [(span["from"], span["to"])])
        restored = sorted(x for x in after - base if station_map[x]["kind"] != "shore")
        restored_priority = sum(int(station_map[x]["priority"]) for x in restored)
        candidates = []
        compatible_seen = False
        weather_seen = False
        current_seen = False
        duration_seen = False
        blackout_free_seen = False
        for ship in ships:
            if int(ship["depth_rating_m"]) < int(span["depth_m"]):
                continue
            kitset = ship["splice_kits"].split("|")
            bonuses = [bonus for kit, bonus in rule_map[span["splice_family"]].items() if kit in kitset]
            if not bonuses:
                continue
            compatible_seen = True
            duration = helper_duration_hours(float(span["length_nm"]))
            for window in windows:
                if window["region"] != span["region"]:
                    continue
                if ship["available_from_utc"] > window["start_utc"]:
                    continue
                if int(ship["max_sea_state"]) < int(window["max_sea_state"]):
                    continue
                weather_seen = True
                cur = current_map.get((span["current_corridor"], window["window_id"]))
                if cur is None or float(cur["mean_mps"]) > float(window["current_limit_mps"]):
                    continue
                current_seen = True
                end_utc = add_hours(window["start_utc"], duration)
                if parse_time(end_utc) > parse_time(window["end_utc"]):
                    continue
                duration_seen = True
                if overlaps_blackout(ship["ship_id"], window["start_utc"], end_utc, mission["blackouts"]):
                    continue
                blackout_free_seen = True
                drift = helper_drift_penalty(float(cur["mean_mps"]), float(cur["bearing_deg"]), int(span["depth_m"]))
                candidates.append({
                    "span_id": span["span_id"],
                    "ship_id": ship["ship_id"],
                    "start_utc": window["start_utc"],
                    "end_utc": end_utc,
                    "splice_family": span["splice_family"],
                    "score": score(
                        int(span["priority_base"]),
                        restored_priority,
                        max(bonuses),
                        drift,
                        int(span["depth_m"]),
                        ship["crew_grade"],
                        hazards.get(span["region"], 0),
                    ),
                    "restored_stations": restored,
                    "reason": "scheduled",
                })
        candidates.sort(key=lambda r: (-r["score"], r["start_utc"], r["ship_id"], r["span_id"]))
        if not compatible_seen:
            fallback = "no-compatible-ship"
        elif not weather_seen:
            fallback = "no-weather-window"
        elif not current_seen:
            fallback = "no-current-window"
        elif not duration_seen:
            fallback = "no-duration-window"
        elif not blackout_free_seen:
            fallback = "ship-blackout"
        else:
            fallback = "ship-window-conflict"
        bundles.append((span, candidates, fallback))
    bundles.sort(key=lambda b: (-(b[1][0]["score"] if b[1] else -999999), b[1][0]["start_utc"] if b[1] else "9999", b[0]["span_id"]))
    busy = defaultdict(list)
    repairs = []
    rejects = []
    for span, candidates, fallback in bundles:
        chosen = None
        for cand in candidates:
            if can_schedule(cand, busy[cand["ship_id"]], mission["cooldown"]):
                busy[cand["ship_id"]].append((cand["start_utc"], cand["end_utc"]))
                chosen = cand
                break
        if chosen:
            repairs.append(chosen)
        else:
            rejects.append({"span_id": span["span_id"], "reason": fallback})
    repairs.sort(key=lambda r: (-r["score"], r["start_utc"], r["span_id"]))
    rejects.sort(key=lambda r: r["span_id"])
    final_edges = ok_edges + [(s["from"], s["to"]) for s in spans if s["span_id"] in {r["span_id"] for r in repairs}]
    final_reach = reachable(shores, final_edges)
    unreachable = sorted(s["station_id"] for s in stations if s["kind"] != "shore" and s["station_id"] not in final_reach)
    lines = []
    for r in repairs:
        lines.append(f"{r['span_id']}|{r['ship_id']}|{r['start_utc']}|{r['end_utc']}|{r['score']}|{';'.join(r['restored_stations'])}")
    for r in rejects:
        lines.append(f"reject|{r['span_id']}|{r['reason']}")
    for u in unreachable:
        lines.append(f"unreachable|{u}")
    return repairs, rejects, unreachable, fnv1a64("\n".join(lines))


@contextmanager
def preserved_files(*paths):
    backups = {}
    for path in paths:
        path = Path(path)
        backups[path] = path.read_text() if path.exists() else None
    try:
        yield
    finally:
        for path, text in backups.items():
            if text is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(text)
        shutil.rmtree(APP / "output", ignore_errors=True)
        shutil.rmtree(APP / "build", ignore_errors=True)


def assert_matches_contract(plan):
    expected_repairs, expected_rejects, expected_unreachable, expected_digest = expected_model()
    assert plan["repair_windows"] == expected_repairs
    assert plan["rejected_repairs"] == expected_rejects
    assert plan["unreachable_stations"] == expected_unreachable
    assert plan["plan_digest"] == expected_digest


def test_schema_and_digest_are_valid():
    """Verify the planner writes the documented JSON schema, actual duration ends, and a canonical digest."""
    plan, _ = run_planner()
    assert set(plan) == {"generated_by", "mission_id", "repair_windows", "unreachable_stations", "rejected_repairs", "plan_digest"}
    assert plan["generated_by"] == "glassreef-planner"
    assert plan["mission_id"] == "glassreef-primary"
    assert isinstance(plan["repair_windows"], list) and plan["repair_windows"], "repair_windows must not be empty"
    assert isinstance(plan["rejected_repairs"], list)
    assert isinstance(plan["unreachable_stations"], list)
    assert re.fullmatch(r"[0-9a-f]{16}", plan["plan_digest"]), plan["plan_digest"]
    weather_ends = {row["end_utc"] for row in read_csv_last_wins(APP / "data/weather/windows.csv", ("window_id",))}
    assert any(repair["end_utc"] not in weather_ends for repair in plan["repair_windows"])
    for repair in plan["repair_windows"]:
        assert set(repair) == {"span_id", "ship_id", "start_utc", "end_utc", "splice_family", "score", "restored_stations", "reason"}
        assert repair["reason"] == "scheduled"
        assert repair["restored_stations"] == sorted(repair["restored_stations"])
        assert parse_time(repair["start_utc"]) < parse_time(repair["end_utc"])
    for rejected in plan["rejected_repairs"]:
        assert set(rejected) == {"span_id", "reason"}
        assert rejected["reason"] in {"no-compatible-ship", "no-weather-window", "no-current-window", "no-duration-window", "ship-blackout", "ship-window-conflict"}


def test_repair_plan_matches_graph_weather_current_splice_hazard_duration_and_mission_policy():
    """Compare the produced repair plan against an independent calculation from all shipped inputs."""
    plan, _ = run_planner()
    assert_matches_contract(plan)


def test_dynamic_feed_overrides_lua_rules_and_hazards_are_live_inputs():
    """Mutate duplicate CSV records, Lua splice rules, and hazard JSON to ensure the plan is not hardcoded."""
    ships = APP / "data/vessels/ships.csv"
    currents = APP / "data/currents/corridors.csv"
    deep_rules = APP / "policies/splice/deep_armor.lua"
    hazard = APP / "data/reference/hazards/hazard_999.json"
    with preserved_files(ships, currents, deep_rules, hazard):
        ships.write_text(ships.read_text() + "RV-MANTA,2026-04-01T00:00Z,KIT-C1|KIT-SHORE|KIT-DEEP,5200,5,A\n")
        currents.write_text(currents.read_text() + "C-GL-03,W-203,0.40,15\n")
        deep_rules.write_text('return {\n  {family="DEEP-ARMOR", kit="KIT-DEEP", bonus=41},\n  {family="DEEP-ARMOR", kit="KIT-B4", bonus=7},\n  {family="DEEP-ARMOR", kit="KIT-C1", bonus=53},\n}\n')
        hazard.write_text(json.dumps({"hazard_id": "HZ-999", "kind": "thermal", "region": "GLASS", "severity": 900, "observed": "2026-03-30T00:00Z"}))
        plan, _ = run_planner()
        assert_matches_contract(plan)
        assert any(r["ship_id"] == "RV-MANTA" and r["splice_family"] == "DEEP-ARMOR" for r in plan["repair_windows"])


def test_compiled_current_helper_is_authoritative():
    """Patch the C drift helper source and verify scores follow the rebuilt helper, not a duplicated formula."""
    current_math = APP / "native/drift/current_math.c"
    with preserved_files(current_math):
        current_math.write_text('''#include "current_math.h"\n#include <math.h>\n\nint glassreef_drift_penalty(double mean_mps, double bearing_deg, int depth_m) {\n    double radians = bearing_deg * 3.14159265358979323846 / 180.0;\n    double directional = fabs(sin(radians)) * 5.0;\n    double depth_component = depth_m > 3000 ? (depth_m - 3000) / 900.0 : 0.0;\n    double raw = mean_mps * 30.0 + directional + depth_component;\n    int base = (int) floor(raw + 0.5);\n    return depth_m >= 3900 ? base + 17 : base;\n}\n''')
        plan, _ = run_planner()
        assert_matches_contract(plan)


def test_duration_helper_profiles_and_mission_constraints_are_authoritative():
    """Patch duration, profile, and mission files so old static-window scheduling and CSV-only priority fail."""
    duration_src = APP / "native/drift/repair_duration.c"
    profile = APP / "data/network/station_profiles/rpt-delta.json"
    mission = APP / "data/missions/glassreef_primary.json"
    with preserved_files(duration_src, profile, mission):
        duration_src.write_text('''double glassreef_duration_hint(double length_nm) {\n    if (length_nm > 50.0) { return 34.0; }\n    if (length_nm > 40.0) { return 17.0; }\n    return 8.0;\n}\n''')
        payload = json.loads(profile.read_text())
        payload["priority"] = 404
        profile.write_text(json.dumps(payload, indent=2) + "\n")
        mission_payload = json.loads(mission.read_text())
        mission_payload["ship_cooldown_hours"] = 9
        mission_payload["ship_blackouts"] = mission_payload.get("ship_blackouts", []) + [
            {"ship_id": "RV-MANTA", "start_utc": "2026-04-05T10:00Z", "end_utc": "2026-04-06T03:00Z"}
        ]
        mission.write_text(json.dumps(mission_payload, indent=2) + "\n")
        plan, _ = run_planner()
        assert_matches_contract(plan)
        assert plan["repair_windows"][0]["span_id"] == "SPAN-007"
        assert plan["repair_windows"][0]["score"] > 1000
        assert any(r["reason"] == "no-duration-window" for r in plan["rejected_repairs"])
        assert all(r["end_utc"] != "2026-04-06T04:00Z" for r in plan["repair_windows"])


def test_report_is_deterministic_and_inputs_are_not_mutated():
    """Run the planner twice and verify JSON bytes stay identical and source feeds are not edited."""
    protected = [
        APP / "data/network/stations.csv",
        APP / "data/network/spans.csv",
        APP / "data/network/station_profiles/rpt-delta.json",
        APP / "data/vessels/ships.csv",
        APP / "data/weather/windows.csv",
        APP / "data/currents/corridors.csv",
        APP / "data/missions/glassreef_primary.json",
        APP / "native/drift/current_math.c",
        APP / "native/drift/repair_duration.c",
        APP / "policies/splice/deep_armor.lua",
    ]
    before = {path: path.read_bytes() for path in protected}
    first, first_text = run_planner()
    second, second_text = run_planner()
    after = {path: path.read_bytes() for path in protected}
    assert first == second
    assert first_text == second_text
    assert before == after
