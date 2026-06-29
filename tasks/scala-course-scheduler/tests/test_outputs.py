"""Verifier for hardened scala-course-scheduler (SUPER-HARD).

Covers JAR + output + 14 hard constraints + score threshold AND:
  - all 28 daemons absent
  - second-layer hard constraints from conflicts, prerequisites, room blackouts, cohorts,
    fixed placements, linked sections, instructor daily loads, and room-zone travel gaps
  - LD_PRELOAD sinkhole removed
  - policy.d/90-final.toml restored to canonical content
  - exactly 16 policy conf.d tiers present
  - HMAC audit chain in schedule verifies against /etc/scheduler/audit.key
  - session_seal field matches recomputed HMAC over fingerprint + audit chain
  - policy_fingerprint matches live effective policy
  - source-integrity: each stub contains its expected primitive call(s)
  - source-integrity: non-stub bugs in Main.scala and DataLoader.scala fixed
  - source-integrity: Bug C in DataLoader.loadCourses fixed (swapped field names)
  - source-integrity: Bug D in AuditKeyLoader.scala fixed (.take(16) removed)
  - source-integrity: Bug E in Policy.scala fixed (* loadBalance → + loadBalance)
  - source-integrity: Bug F in DataLoader.loadRooms fixed (.toInt - 1 → .toInt)
  - course-overrides.csv has only valid field names
  - shell-exec blocklist: no Runtime.exec / ProcessBuilder / scala.sys.process
  - aux cron job removed
  - extra cron job removed
  - hidden daemon archive removed
  - vault archive removed (/opt/scheduler/.vault/)
  - 50-overrides.toml present in conf.d/
  - 97-emergency.toml restored to canonical content
  - 99-runtime.toml restored to canonical hmac_key_path
  - 10-weights.toml restored to canonical load_balance
  - data files intact (courses.json not scrambled, demand.json not corrupted, rooms.json not type-swapped)
  - manifest_hash field present and correct (PBKDF2WithHmacSHA256)
"""
import hashlib
import hmac
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

SCHEDULE_PATH   = Path("/opt/scheduler/schedule.json")
DATA_DIR        = Path("/opt/scheduler")
JAR_PATH        = Path("/app/target/scala-3.3.4/scheduler.jar")
SRC_DIR         = Path("/app/src/main/scala/scheduler")
POLICY_CONF_DIR = Path("/etc/scheduler/conf.d")
HMAC_KEY_PATH   = Path("/etc/scheduler/audit.key")

SLOT_ORDER = {
    "MON-09": 0,
    "MON-11": 1,
    "MON-14": 2,
    "MON-16": 3,
    "WED-09": 4,
    "WED-11": 5,
    "WED-14": 6,
    "WED-16": 7,
}

FIXTURE_HASHES = {
    "conflicts.json": "4f4dbee6e721418fe8c66d1d943788ff362b0b9db69a6b8f17e9653061113a9b",
    "prerequisites.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "room-blackouts.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "cohorts.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "fixed-placements.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "linked-sections.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "instructor-loads.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "room-zones.json": "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356",
}


def load_json(name):
    return json.loads((DATA_DIR / name).read_text())


def expected_constraint_digest(assignments):
    rows = [
        f"{a['course_id']}|{a['room_id']}|{a['time_slot_id']}|{a['instructor_id']}"
        for a in sorted(assignments, key=lambda x: x["course_id"])
    ]
    fixture_part = "|".join(
        f"{name}:{FIXTURE_HASHES[name]}" for name in sorted(FIXTURE_HASHES)
    )
    payload = "\n".join(rows) + "\n--constraints--\n" + fixture_part
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def strip_comments(scala_src: str) -> str:
    """Remove // line comments and /* ... */ block comments before substring scans."""
    s = re.sub(r"/\*.*?\*/", "", scala_src, flags=re.DOTALL)
    s = re.sub(r"//[^\n]*", "", s)
    return s


# ---------------- Build / output basics ----------------

def test_jar_exists():
    """Fat JAR produced by `sbt assembly` lands at the canonical path."""
    assert JAR_PATH.exists(), f"JAR not found at {JAR_PATH} — run: cd /app && sbt assembly"


def test_jar_produces_schedule():
    """Deleting schedule.json and re-running the JAR must regenerate it."""
    SCHEDULE_PATH.unlink(missing_ok=True)
    assert not SCHEDULE_PATH.exists(), "Pre-condition failed: schedule.json could not be removed"
    r = subprocess.run(
        ["java", "-jar", str(JAR_PATH)],
        capture_output=True, text=True, timeout=180,
    )
    assert r.returncode == 0, (
        f"java -jar scheduler.jar failed (rc={r.returncode}). "
        f"stdout={r.stdout[-2000:]!r} stderr={r.stderr[-2000:]!r}"
    )
    assert SCHEDULE_PATH.exists(), "JAR ran successfully but did not write /opt/scheduler/schedule.json"
    data = json.loads(SCHEDULE_PATH.read_text())
    assert isinstance(data.get("assignments"), list) and len(data["assignments"]) > 0, (
        "JAR-produced schedule.json has no assignments"
    )


def test_output_file_exists():
    assert SCHEDULE_PATH.exists(), "schedule.json not found at /opt/scheduler/schedule.json"


def test_output_is_valid_json():
    """schedule.json parses and carries all required top-level keys."""
    data = json.loads(SCHEDULE_PATH.read_text())
    assert "assignments" in data, "Missing 'assignments' key"
    assert "audit_chain" in data, "Missing 'audit_chain' key"
    assert "policy_fingerprint" in data, "Missing 'policy_fingerprint' key"
    assert "session_seal" in data, "Missing 'session_seal' key"
    assert isinstance(data["assignments"], list)
    assert isinstance(data["audit_chain"], list)
    assert isinstance(data["policy_fingerprint"], str)
    assert isinstance(data["session_seal"], str)


def test_output_field_order():
    """Top-level JSON keys must appear in exactly this order:
    assignments, audit_chain, policy_fingerprint, session_seal, audit_tag, manifest_hash, metadata."""
    raw = SCHEDULE_PATH.read_text()
    keys = list(json.loads(raw).keys())
    expected = ["assignments", "audit_chain", "policy_fingerprint", "session_seal", "audit_tag", "manifest_hash", "metadata"]
    assert keys == expected, (
        f"Top-level JSON field order wrong. "
        f"Expected {expected}, got {keys}. "
        f"ScheduleWriter must emit fields in this exact order."
    )


def test_output_metadata_block():
    """ScheduleWriter must emit rich metadata with totals, timestamp, and quality summary."""
    from datetime import datetime
    data = json.loads(SCHEDULE_PATH.read_text())
    assert "metadata" in data, "Missing 'metadata' block in schedule.json"
    m = data["metadata"]
    assert isinstance(m, dict), f"metadata must be an object, got {type(m).__name__}"
    assert "total_courses" in m, "metadata.total_courses missing"
    assert isinstance(m["total_courses"], int), (
        f"metadata.total_courses must be an integer, got {type(m['total_courses']).__name__}"
    )
    assert m["total_courses"] == len(data["assignments"]), (
        f"metadata.total_courses={m['total_courses']} != len(assignments)={len(data['assignments'])}"
    )
    assert "generated_at" in m, "metadata.generated_at missing"
    assert isinstance(m["generated_at"], str), "metadata.generated_at must be a string"
    ts = m["generated_at"].replace("Z", "+00:00")
    try:
        datetime.fromisoformat(ts)
    except ValueError as e:
        raise AssertionError(
            f"metadata.generated_at is not an ISO-8601 timestamp: {m['generated_at']!r} ({e})"
        )
    assert m.get("distinct_slots") == len({a["time_slot_id"] for a in data["assignments"]}), (
        "metadata.distinct_slots must equal the number of unique assigned time slots"
    )
    components = m.get("score_components")
    assert isinstance(components, dict), "metadata.score_components must be an object"
    for key in ("room_util", "faculty_sat", "conflict_avoid", "load_balance"):
        assert key in components, f"metadata.score_components.{key} missing"
        assert isinstance(components[key], (int, float)), (
            f"metadata.score_components.{key} must be numeric"
        )
    digest = m.get("constraint_digest")
    assert isinstance(digest, str) and len(digest) == 64, (
        "metadata.constraint_digest must be a 64-char SHA-256 hex string"
    )
    assert digest == expected_constraint_digest(data["assignments"]), (
        "metadata.constraint_digest must cover sorted assignments and all advanced fixture hashes"
    )


# ---------------- Hard constraints ----------------

def test_all_courses_scheduled():
    """Every course in courses.json is assigned exactly once (constraint 1)."""
    courses = load_json("courses.json")
    schedule = json.loads(SCHEDULE_PATH.read_text())
    assigned = [a["course_id"] for a in schedule["assignments"]]
    expected = {c["id"] for c in courses}
    missing = expected - set(assigned)
    assert not missing, f"Missing courses: {missing}"
    assert len(assigned) == len(courses), \
        f"Expected {len(courses)} assignments, got {len(assigned)}"
    dupes = [c for c, n in Counter(assigned).items() if n > 1]
    assert not dupes, f"Duplicate course assignments: {dupes}"


def test_no_room_double_booking():
    """No (time_slot, room) pair appears twice (constraint 2)."""
    schedule = json.loads(SCHEDULE_PATH.read_text())
    pairs = [(a["time_slot_id"], a["room_id"]) for a in schedule["assignments"]]
    bad = [(k, v) for k, v in Counter(pairs).items() if v > 1]
    assert not bad, f"Room double-booking detected: {bad}"


def test_no_instructor_conflicts():
    """No instructor is assigned to two courses in the same slot (constraint 3)."""
    schedule = json.loads(SCHEDULE_PATH.read_text())
    pairs = [(a["time_slot_id"], a["instructor_id"]) for a in schedule["assignments"]]
    bad = [(k, v) for k, v in Counter(pairs).items() if v > 1]
    assert not bad, f"Instructor conflict detected: {bad}"


def test_instructor_availability_respected():
    """No instructor is scheduled in one of their unavailable_slots (constraint 4)."""
    instructors = {i["id"]: i for i in load_json("instructors.json")}
    schedule = json.loads(SCHEDULE_PATH.read_text())
    bad = []
    for a in schedule["assignments"]:
        instr = instructors.get(a["instructor_id"], {})
        if a["time_slot_id"] in instr.get("unavailable_slots", []):
            bad.append(f"{a['course_id']}: {a['instructor_id']} unavailable at {a['time_slot_id']}")
    assert not bad, f"Availability violations: {bad}"


def test_room_capacity_sufficient():
    """Capacity is checked against the POST-overlay demand."""
    rooms = {r["id"]: r for r in load_json("rooms.json")}
    demand = load_json("demand.json")
    overlay = Path("/etc/scheduler/course-overrides.csv")
    if overlay.exists():
        rows = overlay.read_text().strip().splitlines()[1:]
        for row in rows:
            if not row.strip():
                continue
            parts = row.split(",")
            if len(parts) < 3:
                continue
            cid, field, value = parts[0], parts[1], parts[2]
            if field == "demand" and cid in demand:
                demand[cid] = int(value)
    schedule = json.loads(SCHEDULE_PATH.read_text())
    bad = []
    for a in schedule["assignments"]:
        cap = rooms.get(a["room_id"], {}).get("capacity", 0)
        d = demand.get(a["course_id"], 0)
        if d > cap:
            bad.append(f"{a['course_id']}: demand {d} > {a['room_id']} cap {cap}")
    assert not bad, f"Capacity violations: {bad}"


def test_room_type_matches():
    """Each course is placed in a room whose type equals required_room_type (constraint 6)."""
    rooms = {r["id"]: r for r in load_json("rooms.json")}
    courses = {c["id"]: c for c in load_json("courses.json")}
    schedule = json.loads(SCHEDULE_PATH.read_text())
    bad = []
    for a in schedule["assignments"]:
        req = courses.get(a["course_id"], {}).get("required_room_type")
        got = rooms.get(a["room_id"], {}).get("type")
        if req != got:
            bad.append(f"{a['course_id']}: needs {req}, got {got}")
    assert not bad, f"Room type mismatches: {bad}"


def test_conflict_groups_are_hard_separated():
    """No two courses from any conflict group may share a slot; this is now a hard rule."""
    conflicts = load_json("conflicts.json")
    schedule = json.loads(SCHEDULE_PATH.read_text())
    slot_by_course = {a["course_id"]: a["time_slot_id"] for a in schedule["assignments"]}
    bad = []
    for group in conflicts:
        seen = {}
        for cid in group:
            slot = slot_by_course.get(cid)
            if not slot:
                continue
            if slot in seen:
                bad.append(f"{cid} conflicts with {seen[slot]} at {slot}")
            else:
                seen[slot] = cid
    assert not bad, f"Conflict groups share slots: {bad}"


def test_prerequisite_order_respected():
    """Courses listed in prerequisites.json must be scheduled before their dependents."""
    prereqs = load_json("prerequisites.json")
    schedule = json.loads(SCHEDULE_PATH.read_text())
    slot_by_course = {a["course_id"]: a["time_slot_id"] for a in schedule["assignments"]}
    bad = []
    for edge in prereqs:
        before = edge["before"]
        after = edge["after"]
        gap = int(edge.get("min_gap", 1))
        before_rank = SLOT_ORDER[slot_by_course[before]]
        after_rank = SLOT_ORDER[slot_by_course[after]]
        if after_rank - before_rank < gap:
            bad.append(
                f"{before}@{slot_by_course[before]} must precede "
                f"{after}@{slot_by_course[after]} by {gap} slot(s)"
            )
    assert not bad, f"Prerequisite order violations: {bad}"


def test_room_blackouts_respected():
    """Rooms listed in room-blackouts.json cannot be used in their blocked slots."""
    blackouts = load_json("room-blackouts.json")
    blocked = {b["room_id"]: set(b["blocked_slots"]) for b in blackouts}
    schedule = json.loads(SCHEDULE_PATH.read_text())
    bad = [
        f"{a['course_id']} uses {a['room_id']} at {a['time_slot_id']}"
        for a in schedule["assignments"]
        if a["time_slot_id"] in blocked.get(a["room_id"], set())
    ]
    assert not bad, f"Room blackout violations: {bad}"


def test_cohort_day_spread_respected():
    """Each cohort has a maximum number of its courses allowed on the same day."""
    cohorts = load_json("cohorts.json")
    schedule = json.loads(SCHEDULE_PATH.read_text())
    slot_by_course = {a["course_id"]: a["time_slot_id"] for a in schedule["assignments"]}
    bad = []
    for cohort in cohorts:
        counts = Counter()
        for cid in cohort["courses"]:
            slot = slot_by_course.get(cid)
            if slot:
                counts[slot.split("-", 1)[0]] += 1
        max_per_day = int(cohort["max_per_day"])
        crowded = {day: n for day, n in counts.items() if n > max_per_day}
        if crowded:
            bad.append(f"{cohort['id']}: {crowded} > {max_per_day}")
    assert not bad, f"Cohort day-spread violations: {bad}"


def test_fixed_placements_respected():
    """Fixed placement rows pin selected courses to exact room and slot choices."""
    fixed = load_json("fixed-placements.json")
    schedule = json.loads(SCHEDULE_PATH.read_text())
    by_course = {a["course_id"]: a for a in schedule["assignments"]}
    bad = []
    for row in fixed:
        actual = by_course[row["course_id"]]
        if actual["room_id"] != row["room_id"] or actual["time_slot_id"] != row["time_slot_id"]:
            bad.append(
                f"{row['course_id']}: got {actual['room_id']}@{actual['time_slot_id']}, "
                f"expected {row['room_id']}@{row['time_slot_id']}"
            )
    assert not bad, f"Fixed placement violations: {bad}"


def test_linked_sections_respected():
    """Linked lecture/lab and cross-program pairs must satisfy relation-specific timing."""
    links = load_json("linked-sections.json")
    schedule = json.loads(SCHEDULE_PATH.read_text())
    by_course = {a["course_id"]: a for a in schedule["assignments"]}
    bad = []
    for link in links:
        primary = by_course[link["primary"]]
        secondary = by_course[link["secondary"]]
        p_rank = SLOT_ORDER[primary["time_slot_id"]]
        s_rank = SLOT_ORDER[secondary["time_slot_id"]]
        p_day = primary["time_slot_id"].split("-", 1)[0]
        s_day = secondary["time_slot_id"].split("-", 1)[0]
        if link["relation"] == "same_day_after":
            gap = s_rank - p_rank
            if p_day != s_day or gap < 1 or gap > int(link["max_gap"]):
                bad.append(
                    f"{link['secondary']} must be 1..{link['max_gap']} slots after "
                    f"{link['primary']} on the same day"
                )
        elif link["relation"] == "different_day":
            if p_day == s_day:
                bad.append(f"{link['primary']} and {link['secondary']} must be on different days")
        else:
            bad.append(f"Unknown linked relation {link['relation']}")
    assert not bad, f"Linked section violations: {bad}"


def test_instructor_daily_credit_caps_respected():
    """Instructor daily credit totals cannot exceed instructor-loads.json caps."""
    courses = {c["id"]: c for c in load_json("courses.json")}
    caps = {
        row["instructor_id"]: int(row["max_credits_per_day"])
        for row in load_json("instructor-loads.json")
    }
    schedule = json.loads(SCHEDULE_PATH.read_text())
    credits = Counter()
    for a in schedule["assignments"]:
        day = a["time_slot_id"].split("-", 1)[0]
        credits[(a["instructor_id"], day)] += int(courses[a["course_id"]]["credits"])
    bad = [
        f"{instr} {day}: {total}>{caps[instr]}"
        for (instr, day), total in credits.items()
        if instr in caps and total > caps[instr]
    ]
    assert not bad, f"Instructor daily credit overload: {bad}"


def test_room_zone_travel_gaps_respected():
    """An instructor cannot teach consecutive same-day slots in different room zones."""
    zones = load_json("room-zones.json")
    if not zones:
        return
    schedule = json.loads(SCHEDULE_PATH.read_text())
    by_instr = {}
    for a in schedule["assignments"]:
        by_instr.setdefault(a["instructor_id"], []).append(a)
    bad = []
    for instr, items in by_instr.items():
        ordered = sorted(items, key=lambda x: SLOT_ORDER[x["time_slot_id"]])
        for left, right in zip(ordered, ordered[1:]):
            left_rank = SLOT_ORDER[left["time_slot_id"]]
            right_rank = SLOT_ORDER[right["time_slot_id"]]
            same_day = left["time_slot_id"].split("-", 1)[0] == right["time_slot_id"].split("-", 1)[0]
            if same_day and right_rank - left_rank == 1:
                if zones[left["room_id"]] != zones[right["room_id"]]:
                    bad.append(
                        f"{instr}: {left['course_id']} {left['room_id']} -> "
                        f"{right['course_id']} {right['room_id']}"
                    )
    assert not bad, f"Room-zone travel gap violations: {bad}"


def test_assignments_use_only_enabled_slots():
    """Every assigned slot must come from policy slots.enabled."""
    files = sorted(POLICY_CONF_DIR.glob("*.toml"))
    enabled = None
    for p in files:
        for line in p.read_text().splitlines():
            line = line.strip()
            if line.startswith("enabled"):
                items = re.findall(r'"([^"]+)"', line)
                enabled = items
    assert enabled, "Could not find slots.enabled in any policy file"
    schedule = json.loads(SCHEDULE_PATH.read_text())
    bad = [a["course_id"] for a in schedule["assignments"]
           if a["time_slot_id"] not in enabled]
    assert not bad, f"Assignments use slots outside enabled list: {bad}"


# ---------------- Daemons + LD_PRELOAD ----------------

def test_no_policy_corrupter_running():
    r = subprocess.run(["pgrep", "-f", "scheduler-policy"], capture_output=True)
    assert r.returncode != 0, f"scheduler-policy corrupter is still running: {r.stdout!r}"


def test_no_respawn_watchdog_running():
    r = subprocess.run(["pgrep", "-f", "scheduler-watchdog"], capture_output=True)
    assert r.returncode != 0, f"scheduler-watchdog is still running: {r.stdout!r}"


def test_no_inotify_warden_running():
    r = subprocess.run(["pgrep", "-f", "scheduler-warden"], capture_output=True)
    assert r.returncode != 0, f"scheduler-warden is still running: {r.stdout!r}"


def test_no_binary_corrupter_running():
    """scheduler-binco must be dead so the JAR stays intact after build."""
    r = subprocess.run(["pgrep", "-f", "scheduler-binco"], capture_output=True)
    assert r.returncode != 0, f"scheduler-binco is still running: {r.stdout!r}"


def test_no_source_warden_running():
    """scheduler-srcwa must be dead so Scala implementations are not reverted."""
    r = subprocess.run(["pgrep", "-f", "scheduler-srcwa"], capture_output=True)
    assert r.returncode != 0, f"scheduler-srcwa is still running: {r.stdout!r}"


def test_no_output_corrupter_running():
    """scheduler-outco must be dead so schedule.json is not overwritten."""
    r = subprocess.run(["pgrep", "-f", "scheduler-outco"], capture_output=True)
    assert r.returncode != 0, f"scheduler-outco is still running: {r.stdout!r}"


def test_no_archive_warden_running():
    """scheduler-arcwa must be dead so daemons cannot be auto-resurrected."""
    r = subprocess.run(["pgrep", "-f", "scheduler-arcwa"], capture_output=True)
    assert r.returncode != 0, f"scheduler-arcwa is still running: {r.stdout!r}"


def test_no_chmod_warden_running():
    """scheduler-chmwd must be dead so source files remain writable."""
    r = subprocess.run(["pgrep", "-f", "scheduler-chmwd"], capture_output=True)
    assert r.returncode != 0, f"scheduler-chmwd is still running: {r.stdout!r}"


def test_no_env_saboteur_running():
    """scheduler-envsa must be dead so course-overrides.csv is not corrupted."""
    r = subprocess.run(["pgrep", "-f", "scheduler-envsa"], capture_output=True)
    assert r.returncode != 0, f"scheduler-envsa is still running: {r.stdout!r}"


def test_no_preload_restorer_running():
    """scheduler-ldpres must be dead so ld.so.preload stays cleared."""
    r = subprocess.run(["pgrep", "-f", "scheduler-ldpres"], capture_output=True)
    assert r.returncode != 0, f"scheduler-ldpres is still running: {r.stdout!r}"


def test_no_key_rotator_running():
    """scheduler-keyro must be dead so the HMAC key is not rotated during/after the JAR run."""
    r = subprocess.run(["pgrep", "-f", "scheduler-keyro"], capture_output=True)
    assert r.returncode != 0, f"scheduler-keyro (key-rotator) is still running: {r.stdout!r}"


def test_no_tmp_corrupter_running():
    """scheduler-tmpco must be dead so sbt incremental build caches are not destroyed."""
    r = subprocess.run(["pgrep", "-f", "scheduler-tmpco"], capture_output=True)
    assert r.returncode != 0, f"scheduler-tmpco (tmp-corrupter) is still running: {r.stdout!r}"


def test_no_conf_poisoner_running():
    """scheduler-cfpoi must be dead so 50-overrides.toml remains in conf.d/."""
    r = subprocess.run(["pgrep", "-f", "scheduler-cfpoi"], capture_output=True)
    assert r.returncode != 0, f"scheduler-cfpoi (conf-poisoner) is still running: {r.stdout!r}"


def test_no_output_seal_breaker_running():
    """scheduler-osbr must be dead so session_seal is not zeroed out."""
    r = subprocess.run(["pgrep", "-f", "scheduler-osbr"], capture_output=True)
    assert r.returncode != 0, f"scheduler-osbr (output-seal-breaker) is still running: {r.stdout!r}"


def test_no_bashrc_restorer_running():
    """scheduler-bsrst must be dead so daemon launch hooks are not re-injected into bashrc."""
    r = subprocess.run(["pgrep", "-f", "scheduler-bsrst"], capture_output=True)
    assert r.returncode != 0, f"scheduler-bsrst (bashrc-restorer) is still running: {r.stdout!r}"


def test_no_cron_restorer_running():
    """scheduler-cronr must be dead so cron files are not recreated after removal."""
    r = subprocess.run(["pgrep", "-f", "scheduler-cronr"], capture_output=True)
    assert r.returncode != 0, f"scheduler-cronr (cron-restorer) is still running: {r.stdout!r}"


def test_no_token_refresher_running():
    """scheduler-trefr must be dead so the kill-guard token is not refreshed mid-session."""
    r = subprocess.run(["pgrep", "-f", "scheduler-trefr"], capture_output=True)
    assert r.returncode != 0, f"scheduler-trefr (token-refresher) is still running: {r.stdout!r}"


def test_no_data_scrambler_running():
    """scheduler-dscra must be dead so courses.json lab room-types are not corrupted."""
    r = subprocess.run(["pgrep", "-f", "scheduler-dscra"], capture_output=True)
    assert r.returncode != 0, f"scheduler-dscra (data-scrambler) is still running: {r.stdout!r}"


def test_no_demand_corrupter_running():
    """scheduler-dmcor must be dead so demand.json values are not inflated to 9999."""
    r = subprocess.run(["pgrep", "-f", "scheduler-dmcor"], capture_output=True)
    assert r.returncode != 0, f"scheduler-dmcor (demand-corrupter) is still running: {r.stdout!r}"


def test_no_build_saboteur_running():
    """scheduler-bsabt must be dead so build.sbt is not corrupted by invalid directives."""
    r = subprocess.run(["pgrep", "-f", "scheduler-bsabt"], capture_output=True)
    assert r.returncode != 0, f"scheduler-bsabt (build-saboteur) is still running: {r.stdout!r}"


def test_no_slot_poisoner_running():
    """scheduler-slpoi must be dead so 97-emergency.toml is not overwritten with bad values."""
    r = subprocess.run(["pgrep", "-f", "scheduler-slpoi"], capture_output=True)
    assert r.returncode != 0, f"scheduler-slpoi (slot-poisoner) is still running: {r.stdout!r}"


def test_no_vault_keeper_running():
    """scheduler-vaulk must be dead so the vault archive is not recreated after deletion."""
    r = subprocess.run(["pgrep", "-f", "scheduler-vaulk"], capture_output=True)
    assert r.returncode != 0, f"scheduler-vaulk (vault-keeper) is still running: {r.stdout!r}"


def test_no_conf_scrambler_running():
    """scheduler-confsc must be dead so 10-weights.toml is not corrupted."""
    r = subprocess.run(["pgrep", "-f", "scheduler-confsc"], capture_output=True)
    assert r.returncode != 0, f"scheduler-confsc (conf-scrambler) is still running: {r.stdout!r}"

def test_no_jar_nullifier_running():
    """scheduler-jarnu must be dead so scheduler.jar is not truncated."""
    r = subprocess.run(["pgrep", "-f", "scheduler-jarnu"], capture_output=True)
    assert r.returncode != 0, f"scheduler-jarnu (jar-nullifier) is still running: {r.stdout!r}"

def test_no_source_mangler_running():
    """scheduler-srcma must be dead so AuditKeyLoader.scala stays fixed."""
    r = subprocess.run(["pgrep", "-f", "scheduler-srcma"], capture_output=True)
    assert r.returncode != 0, f"scheduler-srcma (source-mangler) is still running: {r.stdout!r}"

def test_no_conf_merger_running():
    """scheduler-cfmrg must be dead so 99-runtime.toml hmac_key_path stays correct."""
    r = subprocess.run(["pgrep", "-f", "scheduler-cfmrg"], capture_output=True)
    assert r.returncode != 0, f"scheduler-cfmrg (conf-merger) is still running: {r.stdout!r}"

def test_no_cron_extra_running():
    """scheduler-crext must be dead so /etc/cron.d/scheduler-extra is not recreated."""
    r = subprocess.run(["pgrep", "-f", "scheduler-crext"], capture_output=True)
    assert r.returncode != 0, f"scheduler-crext (cron-extra) is still running: {r.stdout!r}"

def test_no_data_mangler_running():
    """scheduler-datmn must be dead so rooms.json types are not swapped."""
    r = subprocess.run(["pgrep", "-f", "scheduler-datmn"], capture_output=True)
    assert r.returncode != 0, f"scheduler-datmn (data-mangler) is still running: {r.stdout!r}"


def test_aux_cron_removed():
    """The secondary /etc/cron.d/scheduler-aux cron job must be removed."""
    p = Path("/etc/cron.d/scheduler-aux")
    assert not p.exists(), (
        "/etc/cron.d/scheduler-aux still exists — a secondary cron will respawn daemons "
        "every 2 minutes even after /etc/cron.d/scheduler-resurrect is removed. "
        "Run: rm -f /etc/cron.d/scheduler-aux"
    )


def test_extra_cron_removed():
    """The tertiary /etc/cron.d/scheduler-extra cron job must be removed."""
    p = Path("/etc/cron.d/scheduler-extra")
    assert not p.exists(), (
        "/etc/cron.d/scheduler-extra still exists — a tertiary cron will respawn daemons "
        "every 3 minutes. Run: rm -f /etc/cron.d/scheduler-extra"
    )


def test_hidden_daemon_archive_removed():
    """The hidden daemon tarball at /opt/scheduler/.hidden/ must be deleted."""
    p = Path("/opt/scheduler/.hidden/daemons.tar.b64")
    assert not p.exists(), (
        "/opt/scheduler/.hidden/daemons.tar.b64 still exists — bashrc-restorer and other "
        "daemons can use this secondary archive to resurrect after the primary archive is gone. "
        "Run: rm -rf /opt/scheduler/.hidden/"
    )


def test_vault_archive_removed():
    """The vault daemon tarball at /opt/scheduler/.vault/ must be deleted."""
    p = Path("/opt/scheduler/.vault/daemons.tar.b64")
    assert not p.exists(), (
        "/opt/scheduler/.vault/daemons.tar.b64 still exists — vault-keeper maintains this "
        "third-layer daemon archive which it recreates from the primary archive every 29 s. "
        "Kill vault-keeper first, then: rm -rf /opt/scheduler/.vault/"
    )


def test_policy_50_overrides_intact():
    """50-overrides.toml must exist in conf.d/ (conf-poisoner hides it as a dot-file)."""
    p = POLICY_CONF_DIR / "50-overrides.toml"
    assert p.exists(), (
        f"50-overrides.toml is missing from {POLICY_CONF_DIR} — "
        f"conf-poisoner may have moved it to .50-overrides.toml.save. "
        f"Restore: mv {POLICY_CONF_DIR}/.50-overrides.toml.save {POLICY_CONF_DIR}/50-overrides.toml"
    )


def test_policy_emergency_restored():
    """97-emergency.toml must be restored to canonical values (pass_score=0.80, 8 enabled slots)."""
    p = POLICY_CONF_DIR / "97-emergency.toml"
    assert p.exists(), (
        f"97-emergency.toml is missing from {POLICY_CONF_DIR} — "
        f"Restore: cp /var/lib/scheduler-resurrect/97-emergency.toml.bak "
        f"/etc/scheduler/conf.d/97-emergency.toml"
    )
    txt = p.read_text()
    assert "pass_score = 0.80" in txt, (
        f"97-emergency.toml has wrong pass_score (slot-poisoner raises it to 0.99). "
        f"Restore: cp /var/lib/scheduler-resurrect/97-emergency.toml.bak "
        f"/etc/scheduler/conf.d/97-emergency.toml\nContent: {txt!r}"
    )
    for slot in ("MON-09", "MON-14", "MON-16", "WED-16"):
        assert slot in txt, (
            f"97-emergency.toml is missing slot {slot!r} (slot-poisoner shrinks list to 2 slots). "
            f"Restore: cp /var/lib/scheduler-resurrect/97-emergency.toml.bak "
            f"/etc/scheduler/conf.d/97-emergency.toml"
        )


def test_99_runtime_toml_restored():
    """99-runtime.toml must have hmac_key_path = /etc/scheduler/audit.key (not /dev/null)."""
    p = POLICY_CONF_DIR / "99-runtime.toml"
    assert p.exists(), (
        f"99-runtime.toml is missing from {POLICY_CONF_DIR}. "
        f"Restore: cp /var/lib/scheduler-resurrect/99-runtime.toml.bak "
        f"/etc/scheduler/conf.d/99-runtime.toml"
    )
    txt = p.read_text()
    assert "/dev/null" not in txt, (
        f"99-runtime.toml has hmac_key_path pointing to /dev/null — "
        f"conf-merger corrupts this file every 23 s. "
        f"Restore: cp /var/lib/scheduler-resurrect/99-runtime.toml.bak "
        f"/etc/scheduler/conf.d/99-runtime.toml\nContent: {txt!r}"
    )
    assert "/etc/scheduler/audit.key" in txt, (
        f"99-runtime.toml must contain hmac_key_path = \"/etc/scheduler/audit.key\". "
        f"Content: {txt!r}"
    )


def test_10_weights_toml_restored():
    """10-weights.toml must have load_balance = 0.15 (not 0.90 from conf-scrambler)."""
    p = POLICY_CONF_DIR / "10-weights.toml"
    assert p.exists(), f"10-weights.toml is missing from {POLICY_CONF_DIR}"
    txt = p.read_text()
    assert "load_balance" in txt, f"10-weights.toml missing load_balance key: {txt!r}"
    for line in txt.splitlines():
        if "load_balance" in line and "=" in line:
            val_str = line.split("=", 1)[1].strip().split()[0]
            try:
                val = float(val_str)
            except ValueError:
                continue
            assert val <= 0.30, (
                f"10-weights.toml has load_balance={val} (conf-scrambler sets it to 0.90). "
                f"Restore: cp /var/lib/scheduler-resurrect/10-weights.toml.bak "
                f"/etc/scheduler/conf.d/10-weights.toml"
            )
            break


def test_data_files_intact():
    """courses.json must have lab-type courses; demand.json must have reasonable values."""
    courses = load_json("courses.json")
    lab_courses = [c for c in courses if c.get("required_room_type") == "lab"]
    assert lab_courses, (
        "courses.json has no courses with required_room_type='lab' — "
        "data-scrambler may have changed all 'lab' entries to 'lecture'. "
        "Restore: cp /var/lib/scheduler-resurrect/courses.json.bak /opt/scheduler/courses.json"
    )
    demand = load_json("demand.json")
    math101_demand = demand.get("MATH101", 0)
    assert math101_demand <= 500, (
        f"demand.json MATH101 demand={math101_demand} (demand-corrupter sets it to 9999). "
        f"Restore: cp /var/lib/scheduler-resurrect/demand.json.bak /opt/scheduler/demand.json"
    )


def test_source_main_correct_chain_order():
    """Main.scala must not sort assignments before building the audit chain."""
    src = _src("Main.scala")
    assert "AuditChain.build" in src, "Main.scala must call AuditChain.build"
    build_idx = src.index("AuditChain.build")
    context = src[max(0, build_idx - 200):build_idx + 200]
    assert ".sortBy" not in context and ".sorted" not in context and ".reverse" not in context, (
        "Main.scala calls AuditChain.build with a sorted or reversed assignment list. "
        "The audit chain MUST be built over assignments in their ORIGINAL optimization order — "
        "not alphabetical or reverse. Remove any .sortBy/.sorted/.reverse before AuditChain.build."
    )


def test_source_dataloader_correct_slot_fields():
    """DataLoader.loadInstructors must read 'preferred_slots' into preferredSlots (not swapped)."""
    src = _src("io/DataLoader.scala")
    pref_idx = src.find('"preferred_slots"')
    unavail_idx = src.find('"unavailable_slots"')
    assert pref_idx >= 0, "DataLoader must reference the 'preferred_slots' JSON field"
    assert unavail_idx >= 0, "DataLoader must reference the 'unavailable_slots' JSON field"
    assert pref_idx < unavail_idx, (
        "DataLoader.loadInstructors has the preferredSlots and unavailableSlots field names "
        "swapped. Fix: Instructor(..., preferredSlots = v(\"preferred_slots\")..., "
        "unavailableSlots = v(\"unavailable_slots\")...)"
    )


def test_source_dataloader_correct_course_fields():
    """DataLoader.loadCourses must read 'required_room_type' before 'instructor_id' (Bug C fix)."""
    src = _src("io/DataLoader.scala")
    rt_idx = src.find('"required_room_type"')
    instr_idx = src.find('"instructor_id"')
    assert rt_idx >= 0, "DataLoader must reference the 'required_room_type' JSON field"
    assert instr_idx >= 0, "DataLoader must reference the 'instructor_id' JSON field"
    assert rt_idx < instr_idx, (
        "DataLoader.loadCourses has the requiredRoomType and instructorId field names swapped "
        "(Bug C). Fix: Course(..., requiredRoomType = v(\"required_room_type\").str, "
        "instructorId = v(\"instructor_id\").str, ...)"
    )


def test_source_audit_key_loader_full_bytes():
    """AuditKeyLoader.scala must NOT truncate the HMAC key to 16 bytes (Bug D fix)."""
    p = SRC_DIR / "io" / "AuditKeyLoader.scala"
    assert p.exists(), (
        "AuditKeyLoader.scala not found at src/main/scala/scheduler/io/AuditKeyLoader.scala — "
        "this non-stub file must exist with Bug D fixed"
    )
    src = strip_comments(p.read_text())
    assert ".take(" not in src, (
        "AuditKeyLoader.scala still contains .take() — Bug D is not fixed. "
        "The load() method must return all bytes of the key, not truncate to 16. "
        "Fix: remove the .take(16) call so `load` returns `all` directly."
    )


def test_source_weights_sum_operator():
    """Policy.scala Weights.sum must use + for all four operands (Bug E: * was used for loadBalance)."""
    p = SRC_DIR / "models" / "Policy.scala"
    assert p.exists(), "Policy.scala not found"
    src = strip_comments(p.read_text())
    assert "def sum" in src, "Weights.sum method not found in Policy.scala"
    sum_start = src.index("def sum")
    sum_context = src[sum_start:sum_start + 200]
    assert "* loadBalance" not in sum_context, (
        "Policy.scala Bug E not fixed: Weights.sum uses `* loadBalance` instead of `+ loadBalance`. "
        "Fix: change `conflictAvoid * loadBalance` to `conflictAvoid + loadBalance` in Policy.scala"
    )


def test_source_dataloader_correct_room_capacity():
    """DataLoader.loadRooms must not subtract 1 from capacity (Bug F off-by-one fix)."""
    src = _src("io/DataLoader.scala")
    assert ".num.toInt - 1" not in src, (
        "DataLoader.scala Bug F not fixed: loadRooms uses `.num.toInt - 1` (off-by-one). "
        "Fix: change `v(\"capacity\").num.toInt - 1` to `v(\"capacity\").num.toInt` in loadRooms."
    )


def test_source_dataloader_real_impl():
    """DataLoader.scala must load all base and advanced scheduling fixtures."""
    src = _src("io/DataLoader.scala")
    assert "loadCourses" in src
    assert "loadRooms" in src
    assert "loadInstructors" in src
    assert "loadDemand" in src
    assert "loadConflicts" in src
    assert "prerequisites.json" in src, (
        "DataLoader must load /opt/scheduler/prerequisites.json for ordering constraints"
    )
    assert "room-blackouts.json" in src, (
        "DataLoader must load /opt/scheduler/room-blackouts.json for room maintenance windows"
    )
    assert "cohorts.json" in src, (
        "DataLoader must load /opt/scheduler/cohorts.json for cohort day-spread limits"
    )
    assert "fixed-placements.json" in src, (
        "DataLoader must load /opt/scheduler/fixed-placements.json for pinned classes"
    )
    assert "linked-sections.json" in src, (
        "DataLoader must load /opt/scheduler/linked-sections.json for lecture/lab relations"
    )
    assert "instructor-loads.json" in src, (
        "DataLoader must load /opt/scheduler/instructor-loads.json for daily credit caps"
    )
    assert "room-zones.json" in src, (
        "DataLoader must load /opt/scheduler/room-zones.json for travel-gap constraints"
    )
    assert '"preferred_slots"' in src
    assert '"unavailable_slots"' in src


def test_audit_tag_present():
    """schedule.json must contain an 'audit_tag' field (FNV-1a-64 over assignments)."""
    data = json.loads(SCHEDULE_PATH.read_text())
    assert "audit_tag" in data, (
        "schedule.json is missing 'audit_tag' field -- "
        "ScheduleWriter must emit a 16-char lowercase hex FNV-1a-64 tag. "
        "See FnvAuditTag.scala stub and ScheduleWriter.write signature."
    )
    tag = data["audit_tag"]
    assert isinstance(tag, str) and len(tag) == 16, (
        f"audit_tag must be exactly 16 lowercase hex chars, got {tag!r}"
    )
    assert tag == tag.lower() and all(c in "0123456789abcdef" for c in tag), (
        f"audit_tag must be lowercase hex only, got {tag!r}"
    )


def test_audit_tag_correct():
    """audit_tag must be the FNV-1a-64 hash of 'course|room|slot|instructor\\n...' for each assignment."""
    data = json.loads(SCHEDULE_PATH.read_text())
    assignments = data["assignments"]
    FNV_PRIME  = 1099511628211
    FNV_OFFSET = 0xcbf29ce484222325
    def fnv1a_64(bs: bytes) -> int:
        h = FNV_OFFSET
        for b in bs:
            h ^= b
            h = (h * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
        return h
    tag_input = "\n".join(
        f"{a['course_id']}|{a['room_id']}|{a['time_slot_id']}|{a['instructor_id']}"
        for a in assignments
    )
    expected = format(fnv1a_64(tag_input.encode("utf-8")), "016x")
    actual = data.get("audit_tag", "")
    assert actual == expected, (
        f"audit_tag mismatch: got {actual!r}, expected {expected!r}. "
        f"Check FnvAuditTag.compute -- use FNV_PRIME=1099511628211, "
        f"FNV_OFFSET=0xcbf29ce484222325, and Long.toUnsignedString for hex output."
    )


def test_manifest_hash_present():
    """schedule.json must contain a 'manifest_hash' field (PBKDF2WithHmacSHA256 seal)."""
    data = json.loads(SCHEDULE_PATH.read_text())
    assert "manifest_hash" in data, (
        "schedule.json is missing 'manifest_hash' field — "
        "ManifestSeal.compute must be called and result written by ScheduleWriter."
    )
    mh = data["manifest_hash"]
    assert isinstance(mh, str) and len(mh) == 64, (
        f"manifest_hash must be exactly 64 lowercase hex chars, got {mh!r}"
    )
    assert mh == mh.lower() and all(c in "0123456789abcdef" for c in mh), (
        f"manifest_hash must be lowercase hex only, got {mh!r}"
    )


def test_manifest_hash_correct():
    """manifest_hash must be PBKDF2WithHmacSHA256 of sorted courseId:roomId:slot:instr, salt=key[:16], iter=4096."""
    import hashlib
    data = json.loads(SCHEDULE_PATH.read_text())
    assignments = data["assignments"]
    key = HMAC_KEY_PATH.read_bytes()
    salt = key[:16]
    sorted_assignments = sorted(assignments, key=lambda a: a["course_id"])
    input_str = "\n".join(
        f"{a['course_id']}:{a['room_id']}:{a['time_slot_id']}:{a['instructor_id']}"
        for a in sorted_assignments
    )
    dk = hashlib.pbkdf2_hmac('sha256', input_str.encode('utf-8'), salt, 4096, dklen=32)
    expected = dk.hex()
    actual = data.get("manifest_hash", "")
    assert actual == expected, (
        f"manifest_hash mismatch: got {actual[:16]!r}…, expected {expected[:16]!r}…. "
        f"Check ManifestSeal.compute — input is assignments sorted by courseId, "
        f"each as 'courseId:roomId:timeSlotId:instructorId', joined with newline. "
        f"Salt = first 16 bytes of /etc/scheduler/audit.key. Iterations=4096, dklen=32."
    )


def test_source_manifest_seal_real_impl():
    """ManifestSeal.scala must implement PBKDF2WithHmacSHA256."""
    src = _src("io/ManifestSeal.scala")
    assert "NotImplementedError" not in src, "ManifestSeal.scala still throws NotImplementedError"
    assert "PBKDF2" in src or "PBEKeySpec" in src or "SecretKeyFactory" in src, (
        "ManifestSeal must use PBKDF2 (PBEKeySpec + SecretKeyFactory)"
    )
    assert "4096" in src, "ManifestSeal must use 4096 PBKDF2 iterations"


def test_source_fnv_audit_tag_real_impl():
    """FnvAuditTag.scala must implement FNV-1a-64 correctly."""
    src = _src("io/FnvAuditTag.scala")
    assert "NotImplementedError" not in src, "FnvAuditTag.scala still throws NotImplementedError"
    assert "1099511628211" in src or "FNV_PRIME" in src.upper() or "fnv" in src.lower(), (
        "FnvAuditTag must use FNV-1a-64 prime (1099511628211)"
    )
    assert "toUnsignedString" in src or "016x" in src or "padTo" in src.lower() or "format" in src, (
        "FnvAuditTag must produce a 16-char unsigned hex string (use Long.toUnsignedString)"
    )


def test_source_assignment_ctor_not_copy():
    """Scheduler.scala must use Assignment(...) constructor directly in multiple
    places — not .copy(). Source-count tests fail when .copy() is used."""
    src = _src("optimizer/Scheduler.scala")
    assert "NotImplementedError" not in src, "Scheduler.scala still throws NotImplementedError"
    count = src.count("Assignment(")
    assert count >= 2, (
        f"Scheduler.scala must call Assignment(...) constructor explicitly at least twice "
        f"(found {count} occurrence). Do NOT use .copy(timeSlotId=...) — "
        "source-count tests verify constructor usage."
    )


def test_ld_preload_sinkhole_removed():
    """/etc/ld.so.preload no longer references libscheduler_guard."""
    p = Path("/etc/ld.so.preload")
    if not p.exists():
        return
    txt = p.read_text()
    assert "libscheduler_guard" not in txt, (
        f"/etc/ld.so.preload still references the guard library: {txt!r}"
    )


def test_bashrc_hooks_removed():
    """Agent must have cleaned daemon-launch hooks from all shell startup files."""
    hook_files = [
        Path("/etc/bash.bashrc"),
        Path("/root/.bashrc"),
    ]
    profile_hook = Path("/etc/profile.d/zz-scheduler-daemons.sh")
    offenders = []
    for p in hook_files:
        if p.exists() and "launch-all" in p.read_text():
            offenders.append(str(p))
    if profile_hook.exists():
        offenders.append(str(profile_hook))
    assert not offenders, (
        f"Daemon-launch hooks still present — daemons will respawn on any new shell: {offenders}. "
        "Remove the launch-all.sh lines from /etc/bash.bashrc and /root/.bashrc, "
        "and delete /etc/profile.d/zz-scheduler-daemons.sh."
    )


# ---------------- Policy file + tier count ----------------

def test_policy_final_restored():
    """90-final.toml carries the canonical undisturbed values."""
    p = POLICY_CONF_DIR / "90-final.toml"
    txt = p.read_text()
    assert "pass_score = 0.80" in txt, f"90-final.toml not restored to pass_score=0.80:\n{txt}"
    assert "room_util       = 0.20" in txt or "room_util = 0.20" in txt
    assert "faculty_sat     = 0.34" in txt or "faculty_sat = 0.34" in txt
    assert "conflict_avoid  = 0.31" in txt or "conflict_avoid = 0.31" in txt
    assert "load_balance    = 0.15" in txt or "load_balance = 0.15" in txt
    assert "MON-09" in txt and "WED-16" in txt


def test_policy_d_has_sixteen_tiers():
    """Exactly sixteen *.toml files must exist under /etc/scheduler/conf.d/."""
    files = sorted(POLICY_CONF_DIR.glob("*.toml"))
    names = [p.name for p in files]
    assert len(files) == 16, (
        f"Expected 16 policy tiers in conf.d/, found {len(files)}: {names}"
    )


def test_course_overrides_csv_intact():
    """course-overrides.csv must have a valid header and only 'demand' field rows
    (env-saboteur may have appended invalid field names)."""
    p = Path("/etc/scheduler/course-overrides.csv")
    assert p.exists(), "course-overrides.csv not found at /etc/scheduler/course-overrides.csv"
    lines = [ln for ln in p.read_text().strip().splitlines() if ln.strip()]
    assert lines, "course-overrides.csv is empty"
    assert lines[0] == "course_id,field,value", (
        f"CSV header invalid: {lines[0]!r} (expected 'course_id,field,value')"
    )
    valid_fields = {"demand"}
    for line in lines[1:]:
        parts = line.split(",")
        assert len(parts) >= 2, f"Malformed row in course-overrides.csv: {line!r}"
        assert parts[1] in valid_fields, (
            f"Invalid field {parts[1]!r} in course-overrides.csv — "
            f"env-saboteur may have corrupted it (row: {line!r})"
        )


# ---------------- Audit chain + fingerprint + session seal ----------------

def test_audit_chain_length_matches_assignments():
    """The audit chain has one link per assignment."""
    schedule = json.loads(SCHEDULE_PATH.read_text())
    assert len(schedule["audit_chain"]) == len(schedule["assignments"]), (
        f"audit_chain length {len(schedule['audit_chain'])} != "
        f"assignments length {len(schedule['assignments'])}"
    )


def test_audit_chain_verifies():
    """Each audit_chain link matches HMAC-SHA256(key, 'prev|course|room|slot|instructor')."""
    schedule = json.loads(SCHEDULE_PATH.read_text())
    chain = schedule["audit_chain"]
    assignments = schedule["assignments"]
    key = HMAC_KEY_PATH.read_bytes()
    prev = "GENESIS"
    for i, (a, link) in enumerate(zip(assignments, chain)):
        assert link.get("course_id") == a["course_id"], (
            f"audit_chain[{i}].course_id != assignments[{i}].course_id"
        )
        payload = (
            f"{prev}|{a['course_id']}|{a['room_id']}|"
            f"{a['time_slot_id']}|{a['instructor_id']}"
        )
        expected = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
        assert link.get("hmac") == expected, (
            f"audit_chain[{i}] HMAC mismatch for course {a['course_id']}: "
            f"expected {expected[:16]}…, got {link.get('hmac', '')[:16]}…"
        )
        prev = expected


def test_audit_chain_has_seq_field():
    """Each audit_chain link must carry a 0-based integer 'seq' field."""
    schedule = json.loads(SCHEDULE_PATH.read_text())
    chain = schedule["audit_chain"]
    for i, link in enumerate(chain):
        assert "seq" in link, (
            f"audit_chain[{i}] is missing the required 'seq' field — "
            f"every link must include a 0-based integer index"
        )
        assert isinstance(link["seq"], int), (
            f"audit_chain[{i}].seq must be an integer, got {type(link['seq']).__name__}"
        )
        assert link["seq"] == i, (
            f"audit_chain[{i}].seq={link['seq']} but expected {i} "
            f"(seq is the 0-based position in the chain)"
        )


def test_session_seal_matches():
    """session_seal covers the policy fingerprint and the full audit chain (with seq)."""
    schedule = json.loads(SCHEDULE_PATH.read_text())
    key = HMAC_KEY_PATH.read_bytes()
    fp = schedule["policy_fingerprint"]
    chain = schedule["audit_chain"]
    n = len(schedule["assignments"])
    # Each entry is "seq:course_id:hmac" (three colon-separated parts).
    chain_str = "|".join(f"{lnk['seq']}:{lnk['course_id']}:{lnk['hmac']}" for lnk in chain)
    payload = f"seal:{fp}|{n}|{chain_str}"
    expected = hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    assert schedule.get("session_seal") == expected, (
        f"session_seal mismatch — "
        f"got {schedule.get('session_seal', '(missing)')[:16]}…, "
        f"expected {expected[:16]}…\n"
        f"Payload prefix: {payload[:80]!r}\n"
        f"HINT: chain entries must be 'seq:course_id:hmac', not 'course_id:hmac'"
    )


def test_policy_fingerprint_matches_live_policy():
    """Recompute the canonical fingerprint of the live policy and compare."""
    files = sorted(POLICY_CONF_DIR.glob("*.toml"))
    merged = {}
    for p in files:
        section = None
        for raw in p.read_text().splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            m = re.match(r"\[([A-Za-z_][A-Za-z0-9_.]*)\]", line)
            if m:
                section = m.group(1)
                merged.setdefault(section, {})
                continue
            if section is None:
                continue
            m = re.match(r'([A-Za-z_]\w*)\s*=\s*\[(.*)\]', line)
            if m:
                merged[section][m.group(1)] = re.findall(r'"([^"]+)"', m.group(2))
                continue
            m = re.match(r'([A-Za-z_]\w*)\s*=\s*"((?:[^"\\]|\\.)*)"', line)
            if m:
                merged[section][m.group(1)] = m.group(2)
                continue
            m = re.match(r'([A-Za-z_]\w*)\s*=\s*([+-]?\d+(?:\.\d+)?)', line)
            if m:
                v = m.group(2)
                merged[section][m.group(1)] = float(v) if "." in v else int(v)

    w = merged["weights"]
    canon = (
        f"threshold={float(merged['threshold']['pass_score']):.4f}"
        f";weights=ru:{float(w['room_util']):.4f}"
        f",fs:{float(w['faculty_sat']):.4f}"
        f",ca:{float(w['conflict_avoid']):.4f}"
        f",lb:{float(w['load_balance']):.4f}"
        f";slots={','.join(merged['slots']['enabled'])}"
    )
    expected = hashlib.sha256(canon.encode("utf-8")).hexdigest()
    schedule = json.loads(SCHEDULE_PATH.read_text())
    assert schedule["policy_fingerprint"] == expected, (
        f"policy_fingerprint mismatch: schedule={schedule['policy_fingerprint'][:16]}…, "
        f"expected={expected[:16]}…"
    )


# ---------------- Source-integrity assertions ----------------

def _src(rel):
    return strip_comments((SRC_DIR / rel).read_text())


def test_source_policy_loader_real_impl():
    """PolicyLoader.scala is implemented and merges conf.d/ files in lexical order."""
    src = _src("io/PolicyLoader.scala")
    assert "NotImplementedError" not in src, "PolicyLoader.scala still throws NotImplementedError"
    assert "EffectivePolicy" in src
    assert "weights" in src and "threshold" in src and "slots" in src
    assert ".sortBy" in src or ".sorted" in src, (
        "PolicyLoader must merge files in lex order — sort missing"
    )


def test_overlay_demand_applied_to_schedule():
    """Demand overrides in course-overrides.csv reach the optimizer."""
    import csv as _csv
    demand_original = load_json("demand.json")
    overlay_path = Path("/etc/scheduler/course-overrides.csv")
    overridden: dict[str, int] = {}
    if overlay_path.exists():
        for row in _csv.DictReader(overlay_path.open()):
            if row["field"] == "demand" and row["course_id"] in demand_original:
                overridden[row["course_id"]] = int(row["value"])
    assert overridden, "No demand overrides found in course-overrides.csv — check fixture"

    rooms = {r["id"]: r for r in load_json("rooms.json")}
    schedule = json.loads(SCHEDULE_PATH.read_text())
    assigned_room = {a["course_id"]: a["room_id"] for a in schedule["assignments"]}

    violations = []
    for cid, new_demand in overridden.items():
        rid = assigned_room.get(cid)
        if rid is None:
            continue
        cap = rooms.get(rid, {}).get("capacity", 0)
        if cap < new_demand:
            violations.append(
                f"{cid}: overridden demand {new_demand} > room {rid} capacity {cap}"
            )
    assert not violations, (
        f"Demand overlay was not applied before course placement: {violations}"
    )


def test_source_audit_chain_real_impl():
    """AuditChain.scala uses javax.crypto Mac with HmacSHA256, seeds prev with GENESIS,
    and includes a 'seq' field in every chain link."""
    src = _src("io/AuditChain.scala")
    assert "NotImplementedError" not in src
    assert "HmacSHA256" in src, "AuditChain must use HmacSHA256"
    assert "GENESIS" in src, "AuditChain must seed prev with 'GENESIS'"
    assert "Mac" in src and "doFinal" in src
    assert '"seq"' in src or "seq" in src, (
        "AuditChain.build must include a 'seq' field (0-based index) in each chain link"
    )


def test_source_session_sealer_real_impl():
    """SessionSealer.scala uses HmacSHA256 and prefixes the payload with 'seal:'."""
    src = _src("io/SessionSealer.scala")
    assert "NotImplementedError" not in src, "SessionSealer.scala still throws NotImplementedError"
    assert "HmacSHA256" in src, "SessionSealer must use HmacSHA256"
    assert "seal:" in src, "SessionSealer payload must start with 'seal:'"
    assert "Mac" in src and "doFinal" in src


def test_source_canonical_real_impl():
    """Canonical.scala builds the canonical policy string and hashes it with SHA-256."""
    src = _src("policy/Canonical.scala")
    assert "NotImplementedError" not in src
    assert "SHA-256" in src or "SHA256" in src
    assert "%.4f" in src or "0.0000" in src or "Locale" in src, (
        "Canonical.fingerprint must format doubles with %.4f"
    )
    assert "threshold=" in src and "weights=" in src and "slots=" in src


def test_source_soft_scorer_real_impl():
    """SoftScorer.scala references the effective weights and instructor preferredSlots."""
    src = _src("optimizer/SoftScorer.scala")
    assert "NotImplementedError" not in src
    assert "weights.roomUtil" in src or "weights.facultySat" in src
    assert "preferredSlots" in src


def test_source_constraint_checker_real_impl():
    """ConstraintChecker.scala consults all hard constraints, including advanced fixtures."""
    src = _src("optimizer/ConstraintChecker.scala")
    assert "NotImplementedError" not in src
    assert "unavailableSlots" in src
    assert "capacity" in src.lower()
    assert "blackout" in src.lower() or "blockedSlots" in src or "blocked_slots" in src, (
        "ConstraintChecker must reject room blackout slots"
    )
    assert "prereq" in src.lower() or "prerequisite" in src.lower() or "min_gap" in src, (
        "ConstraintChecker must enforce prerequisite ordering"
    )
    assert "cohort" in src.lower() and "max" in src.lower(), (
        "ConstraintChecker must enforce cohort max_per_day spread rules"
    )
    assert "fixed" in src.lower() or "pinned" in src.lower(), (
        "ConstraintChecker must enforce fixed placement rows"
    )
    assert "linked" in src.lower() or "same_day_after" in src or "different_day" in src, (
        "ConstraintChecker must enforce linked section relations"
    )
    assert "credit" in src.lower() and ("daily" in src.lower() or "day" in src.lower()), (
        "ConstraintChecker must enforce instructor daily credit caps"
    )
    assert "zone" in src.lower() and ("travel" in src.lower() or "consecutive" in src.lower()), (
        "ConstraintChecker must enforce room-zone travel gaps"
    )


def test_source_scheduler_uses_second_layer_constraints():
    """Scheduler.scala must thread and optimize against advanced hard constraints."""
    src = _src("optimizer/Scheduler.scala")
    assert "NotImplementedError" not in src
    for token in ("conflicts", "blackout", "prereq", "cohort", "fixed", "linked", "credit", "zone"):
        assert token.lower() in src.lower(), (
            f"Scheduler.scala must account for {token} constraints during placement/search"
        )
    assert "SLOT_ORDER" in src or "slotOrder" in src or "indexOf" in src or "zipWithIndex" in src, (
        "Scheduler.scala must compare slot ordering for prerequisite min_gap checks"
    )


def test_scheduler_distributes_across_slots():
    """The optimizer spreads courses across multiple enabled time slots."""
    schedule = json.loads(SCHEDULE_PATH.read_text())
    assignments = schedule["assignments"]

    required_fields = {"course_id", "room_id", "time_slot_id", "instructor_id"}
    bad_fields = [
        f"index {i} missing {required_fields - set(a)}"
        for i, a in enumerate(assignments)
        if not required_fields.issubset(a)
    ]
    assert not bad_fields, f"Assignments missing required fields: {bad_fields}"

    slots_used = {a["time_slot_id"] for a in assignments}
    assert len(slots_used) >= 3, (
        f"Schedule uses only {len(slots_used)} distinct time slot(s) — "
        "a feasible optimizer must distribute courses across multiple slots"
    )


def test_source_schedule_writer_real_impl():
    """ScheduleWriter.scala emits assignments, audit fields, metadata, score components, and constraint digest."""
    src = _src("io/ScheduleWriter.scala")
    assert "NotImplementedError" not in src
    assert "audit_chain" in src and "policy_fingerprint" in src
    assert "session_seal" in src, "ScheduleWriter must emit a 'session_seal' field"
    assert "audit_tag" in src, "ScheduleWriter must emit an 'audit_tag' field (FNV-1a-64)"
    assert "manifest_hash" in src, "ScheduleWriter must emit a 'manifest_hash' field (PBKDF2)"
    assert "metadata" in src and "total_courses" in src
    assert "score_components" in src and "constraint_digest" in src, (
        "ScheduleWriter metadata must include score_components and constraint_digest"
    )


def test_no_shell_exec_in_scala_sources():
    """The agent must NOT shell out from inside the JAR."""
    blocked_patterns = [
        "Runtime.getRuntime",
        "ProcessBuilder",
        "scala.sys.process",
        "import sys.process",
        "java.lang.Runtime",
    ]
    offenders = []
    for p in SRC_DIR.rglob("*.scala"):
        text = strip_comments(p.read_text())
        for pat in blocked_patterns:
            if pat in text:
                offenders.append((str(p.relative_to(SRC_DIR)), pat))
    assert not offenders, (
        f"Forbidden shell/exec patterns found in Scala sources: {offenders}"
    )


# ---------------- Soft score threshold ----------------

def test_score_meets_threshold():
    """model.py exits 0 — soft score, audit chain, and policy_fingerprint all check out."""
    result = subprocess.run(
        ["python3", "/opt/scheduler/model.py", str(SCHEDULE_PATH)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"model.py failed (rc={result.returncode}). "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
