#!/usr/bin/env python3
"""Scoring model for the hardened scala-course-scheduler.

The model reads the effective policy by lex-merging every *.toml under
/etc/scheduler/conf.d and verifies:
  1. the schedule's policy_fingerprint matches the live effective policy
  2. the HMAC-SHA256 audit chain is intact and signs the assignments
  3. the hard-constraint-derived soft score components meet the threshold

The input data files under /opt/scheduler are SHA-256 pinned so the agent
cannot modify them to game the score.
"""
import hashlib
import hmac
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

DATA_DIR        = Path("/opt/scheduler")
POLICY_CONF_DIR = Path("/etc/scheduler/conf.d")
HMAC_KEY_PATH   = Path("/etc/scheduler/audit.key")

_EXPECTED_HASHES = {
    "rooms.json":          "71468eb186c2b994fd44ed57ef571211c91ca8bc23b5fee6386223ace0e2b1a4",
    "courses.json":        "cd07285432b7efb87fd2a49400e203d09241344e83c9b9db204208bb545d8ccd",
    "instructors.json":    "8c62f440b5af30cb2cd45dadfe1b1457868c83ecdc2d65a4ac3d8888ffb739c3",
    "demand.json":         "11fc7bc84518e4236bc23c7ab008370035a8688f65673ab30bb97d63bafb4ce8",
    "conflicts.json":      "4f4dbee6e721418fe8c66d1d943788ff362b0b9db69a6b8f17e9653061113a9b",
    "prerequisites.json":  "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "room-blackouts.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "cohorts.json":        "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "fixed-placements.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "linked-sections.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "instructor-loads.json": "37517e5f3dc66819f61f5a7bb8ace1921282415f10551d2defa5c3eb0985b570",
    "room-zones.json": "ca3d163bab055381827226140568f3bef7eaac187cebd76878e0b63e9e442356",
}

_SLOT_ORDER = {
    "MON-09": 0,
    "MON-11": 1,
    "MON-14": 2,
    "MON-16": 3,
    "WED-09": 4,
    "WED-11": 5,
    "WED-14": 6,
    "WED-16": 7,
}


def slot_day(slot_id):
    return slot_id.split("-", 1)[0]


def constraint_digest(assignments):
    rows = [
        f"{a['course_id']}|{a['room_id']}|{a['time_slot_id']}|{a['instructor_id']}"
        for a in sorted(assignments, key=lambda x: x["course_id"])
    ]
    fixture_part = "|".join(
        f"{name}:{_EXPECTED_HASHES[name]}"
        for name in sorted(_EXPECTED_HASHES)
        if name not in {"rooms.json", "courses.json", "instructors.json", "demand.json"}
    )
    payload = "\n".join(rows) + "\n--constraints--\n" + fixture_part
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def verify_hard_extensions(assignments, conflicts):
    by_course = {a["course_id"]: a for a in assignments}
    courses = {c["id"]: c for c in load_json("courses.json")}

    for group in conflicts:
        slots = {}
        for cid in group:
            if cid not in by_course:
                continue
            slot = by_course[cid]["time_slot_id"]
            if slot in slots:
                raise RuntimeError(
                    f"conflict group hard violation: {cid} and {slots[slot]} both at {slot}"
                )
            slots[slot] = cid

    blackouts = load_json("room-blackouts.json")
    blocked = {
        item["room_id"]: set(item.get("blocked_slots", []))
        for item in blackouts
    }
    for a in assignments:
        if a["time_slot_id"] in blocked.get(a["room_id"], set()):
            raise RuntimeError(
                f"room blackout violation: {a['room_id']} unavailable at "
                f"{a['time_slot_id']} for {a['course_id']}"
            )

    for edge in load_json("prerequisites.json"):
        before = edge["before"]
        after = edge["after"]
        if before not in by_course or after not in by_course:
            continue
        gap = int(edge.get("min_gap", 1))
        before_rank = _SLOT_ORDER.get(by_course[before]["time_slot_id"], -100)
        after_rank = _SLOT_ORDER.get(by_course[after]["time_slot_id"], -100)
        if after_rank - before_rank < gap:
            raise RuntimeError(
                f"prerequisite order violation: {before} at "
                f"{by_course[before]['time_slot_id']} must precede {after} at "
                f"{by_course[after]['time_slot_id']} by at least {gap} slot(s)"
            )

    for cohort in load_json("cohorts.json"):
        max_per_day = int(cohort.get("max_per_day", 99))
        day_counts = Counter()
        for cid in cohort.get("courses", []):
            if cid in by_course:
                day_counts[slot_day(by_course[cid]["time_slot_id"])] += 1
        crowded = {day: n for day, n in day_counts.items() if n > max_per_day}
        if crowded:
            raise RuntimeError(
                f"cohort {cohort['id']} exceeds max_per_day={max_per_day}: {crowded}"
            )

    for fixed in load_json("fixed-placements.json"):
        cid = fixed["course_id"]
        a = by_course.get(cid)
        if not a:
            continue
        for field in ("room_id", "time_slot_id"):
            if a[field] != fixed[field]:
                raise RuntimeError(
                    f"fixed placement violation: {cid} {field}={a[field]} "
                    f"expected {fixed[field]}"
                )

    for link in load_json("linked-sections.json"):
        primary = by_course.get(link["primary"])
        secondary = by_course.get(link["secondary"])
        if not primary or not secondary:
            continue
        p_rank = _SLOT_ORDER[primary["time_slot_id"]]
        s_rank = _SLOT_ORDER[secondary["time_slot_id"]]
        relation = link["relation"]
        max_gap = int(link.get("max_gap", 8))
        if relation == "same_day_after":
            same_day = slot_day(primary["time_slot_id"]) == slot_day(secondary["time_slot_id"])
            gap = s_rank - p_rank
            if not same_day or gap < 1 or gap > max_gap:
                raise RuntimeError(
                    f"linked section violation: {link['secondary']} must be "
                    f"1..{max_gap} slots after {link['primary']} on the same day"
                )
        elif relation == "different_day":
            if slot_day(primary["time_slot_id"]) == slot_day(secondary["time_slot_id"]):
                raise RuntimeError(
                    f"linked section violation: {link['primary']} and "
                    f"{link['secondary']} must be on different days"
                )
        else:
            raise RuntimeError(f"unknown linked-section relation: {relation}")

    load_caps = {
        item["instructor_id"]: int(item["max_credits_per_day"])
        for item in load_json("instructor-loads.json")
    }
    credits_by_instr_day = Counter()
    for a in assignments:
        credits = int(courses[a["course_id"]]["credits"])
        credits_by_instr_day[(a["instructor_id"], slot_day(a["time_slot_id"]))] += credits
    overloaded = [
        f"{instr} {day}: {credits}>{load_caps[instr]}"
        for (instr, day), credits in credits_by_instr_day.items()
        if instr in load_caps and credits > load_caps[instr]
    ]
    if overloaded:
        raise RuntimeError(f"instructor daily credit overload: {overloaded}")

    zones = load_json("room-zones.json")
    by_instr = {}
    for a in assignments:
        by_instr.setdefault(a["instructor_id"], []).append(a)
    travel_bad = []
    for instr, items in by_instr.items():
        ordered = sorted(items, key=lambda x: _SLOT_ORDER[x["time_slot_id"]])
        for left, right in zip(ordered, ordered[1:]):
            left_rank = _SLOT_ORDER[left["time_slot_id"]]
            right_rank = _SLOT_ORDER[right["time_slot_id"]]
            if right_rank - left_rank == 1 and slot_day(left["time_slot_id"]) == slot_day(right["time_slot_id"]):
                if zones.get(left["room_id"]) != zones.get(right["room_id"]):
                    travel_bad.append(
                        f"{instr}: {left['course_id']} {left['room_id']} -> "
                        f"{right['course_id']} {right['room_id']}"
                    )
    if travel_bad:
        raise RuntimeError(f"room-zone travel gap violations: {travel_bad}")


def verify_input_integrity():
    for filename, expected in _EXPECTED_HASHES.items():
        path = DATA_DIR / filename
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(
                f"Input file {filename} has been modified. "
                "Do not edit files under /opt/scheduler/."
            )


_KV_NUM    = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([+-]?\d+(?:\.\d+)?)\s*(?:#.*)?$')
_KV_STR    = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"((?:[^"\\]|\\.)*)"\s*(?:#.*)?$')
_KV_LIST   = re.compile(r'^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\[(.*)\]\s*(?:#.*)?$')
_SECTION   = re.compile(r'^\s*\[([A-Za-z_][A-Za-z0-9_.]*)\]\s*$')
_LIST_ITEM = re.compile(r'"([^"]*)"')


def parse_simple_toml(text):
    out = {}
    section = None
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip() if not raw.strip().startswith("#") else ""
        if not line.strip():
            continue
        m = _SECTION.match(line)
        if m:
            section = m.group(1)
            out.setdefault(section, {})
            continue
        if section is None:
            continue
        m = _KV_LIST.match(line)
        if m:
            out[section][m.group(1)] = _LIST_ITEM.findall(m.group(2))
            continue
        m = _KV_STR.match(line)
        if m:
            out[section][m.group(1)] = m.group(2)
            continue
        m = _KV_NUM.match(line)
        if m:
            v = m.group(2)
            out[section][m.group(1)] = float(v) if "." in v else int(v)
            continue
    return out


def load_effective_policy():
    merged = {}
    files = sorted(POLICY_CONF_DIR.glob("*.toml"))
    if not files:
        raise RuntimeError(f"No policy files found under {POLICY_CONF_DIR}")
    for p in files:
        cfg = parse_simple_toml(p.read_text())
        for section, kv in cfg.items():
            merged.setdefault(section, {})
            merged[section].update(kv)

    try:
        w = merged["weights"]
        eff = {
            "room_util":      float(w["room_util"]),
            "faculty_sat":    float(w["faculty_sat"]),
            "conflict_avoid": float(w["conflict_avoid"]),
            "load_balance":   float(w["load_balance"]),
            "pass_score":     float(merged["threshold"]["pass_score"]),
            "enabled_slots":  list(merged["slots"]["enabled"]),
            "hmac_key_path":  merged["audit"]["hmac_key_path"],
            "overlay_csv":    merged["overlay"]["course_overrides_csv"],
        }
    except KeyError as e:
        raise RuntimeError(f"Effective policy missing required key: {e}")

    if abs(eff["room_util"] + eff["faculty_sat"]
           + eff["conflict_avoid"] + eff["load_balance"] - 1.0) > 1e-6:
        raise RuntimeError("Effective policy weights do not sum to 1.0")

    return eff


def canonical_fingerprint(eff):
    s = (
        f"threshold={eff['pass_score']:.4f}"
        f";weights=ru:{eff['room_util']:.4f}"
        f",fs:{eff['faculty_sat']:.4f}"
        f",ca:{eff['conflict_avoid']:.4f}"
        f",lb:{eff['load_balance']:.4f}"
        f";slots={','.join(eff['enabled_slots'])}"
    )
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def verify_audit_chain(assignments, chain, key_bytes):
    if len(chain) != len(assignments):
        raise RuntimeError(
            f"audit_chain length {len(chain)} != assignments length {len(assignments)}"
        )
    prev = "GENESIS"
    for i, (a, link) in enumerate(zip(assignments, chain)):
        if link.get("seq") != i:
            raise RuntimeError(
                f"audit_chain[{i}] seq mismatch: "
                f"got {link.get('seq')!r}, expected {i}"
            )
        if link.get("course_id") != a["course_id"]:
            raise RuntimeError(
                f"audit_chain[{i}] course_id mismatch: "
                f"{link.get('course_id')} != {a['course_id']}"
            )
        payload = (f"{prev}|{a['course_id']}|{a['room_id']}|"
                   f"{a['time_slot_id']}|{a['instructor_id']}")
        expected = hmac.new(
            key_bytes, payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if link.get("hmac") != expected:
            raise RuntimeError(
                f"audit_chain[{i}] HMAC invalid for course {a['course_id']}"
            )
        prev = expected


def load_json(filename):
    with open(DATA_DIR / filename) as f:
        return json.load(f)


def apply_overlay(demand, overlay_path):
    p = Path(overlay_path) if overlay_path else None
    if not p or not p.exists():
        return demand
    out = dict(demand)
    text = p.read_text().strip().splitlines()
    if not text:
        return out
    header = text[0].strip().split(",")
    if header != ["course_id", "field", "value"]:
        raise RuntimeError(f"Overlay CSV header invalid: {header}")
    for row in text[1:]:
        if not row.strip():
            continue
        cid, field, value = row.strip().split(",")
        if cid not in out:
            continue
        if field == "demand":
            out[cid] = int(value)
        else:
            raise RuntimeError(f"Overlay CSV unknown field: {row}")
    return out


def score_schedule(schedule_path):
    verify_input_integrity()
    eff = load_effective_policy()

    with open(schedule_path) as f:
        schedule = json.load(f)

    assignments = schedule.get("assignments", [])
    if not assignments:
        return 0.0

    actual_fp = schedule.get("policy_fingerprint", "")
    expected_fp = canonical_fingerprint(eff)
    if actual_fp != expected_fp:
        raise RuntimeError(
            f"policy_fingerprint mismatch: schedule={actual_fp[:16]}... "
            f"expected={expected_fp[:16]}... "
            "(effective policy on disk has changed since the schedule was produced)"
        )

    chain = schedule.get("audit_chain", [])
    key_bytes = HMAC_KEY_PATH.read_bytes()
    verify_audit_chain(assignments, chain, key_bytes)

    metadata = schedule.get("metadata", {})
    expected_digest = constraint_digest(assignments)
    if metadata.get("constraint_digest") != expected_digest:
        raise RuntimeError(
            f"metadata.constraint_digest mismatch: got "
            f"{metadata.get('constraint_digest', '')[:16]}... expected {expected_digest[:16]}..."
        )

    # Verify session_seal
    seal = schedule.get("session_seal", "")
    if not seal:
        raise RuntimeError("schedule.json is missing 'session_seal' field")
    n = len(assignments)
    chain_str = "|".join(f"{lnk['seq']}:{lnk['course_id']}:{lnk['hmac']}" for lnk in chain)
    seal_payload = f"seal:{actual_fp}|{n}|{chain_str}"
    expected_seal = hmac.new(
        key_bytes, seal_payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if seal != expected_seal:
        raise RuntimeError(
            f"session_seal mismatch: got {seal[:16]}... expected {expected_seal[:16]}..."
        )

    # Verify FNV-1a-64 audit tag
    audit_tag = schedule.get("audit_tag", "")
    if not audit_tag:
        raise RuntimeError("schedule.json is missing 'audit_tag' field")
    FNV_PRIME  = 1099511628211
    FNV_OFFSET = 0xcbf29ce484222325
    def fnv1a_64(data: bytes) -> int:
        h = FNV_OFFSET
        for b in data:
            h ^= b
            h = (h * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
        return h
    tag_input = "\n".join(
        f"{a['course_id']}|{a['room_id']}|{a['time_slot_id']}|{a['instructor_id']}"
        for a in assignments
    )
    expected_tag = format(fnv1a_64(tag_input.encode("utf-8")), "016x")
    if audit_tag != expected_tag:
        raise RuntimeError(
            f"audit_tag mismatch: got {audit_tag!r}, expected {expected_tag!r}"
        )

    rooms       = {r["id"]: r for r in load_json("rooms.json")}
    instructors = {i["id"]: i for i in load_json("instructors.json")}
    demand      = apply_overlay(load_json("demand.json"), eff["overlay_csv"])
    conflicts   = load_json("conflicts.json")

    verify_hard_extensions(assignments, conflicts)

    util_scores = []
    for a in assignments:
        room = rooms.get(a["room_id"], {})
        cap = room.get("capacity", 1)
        d = demand.get(a["course_id"], 0)
        util_scores.append(min(1.0, d / cap))
    room_util = sum(util_scores) / len(util_scores) if util_scores else 0.0

    fac_scores = []
    for a in assignments:
        instr = instructors.get(a["instructor_id"], {})
        preferred = instr.get("preferred_slots", [])
        fac_scores.append(1.0 if a["time_slot_id"] in preferred else 0.5)
    fac_sat = sum(fac_scores) / len(fac_scores) if fac_scores else 0.0

    slot_map = {a["course_id"]: a["time_slot_id"] for a in assignments}
    conflict_hits = 0
    for group in conflicts:
        if len(group) >= 2:
            slots_in_group = [slot_map.get(c) for c in group if c in slot_map]
            if len(slots_in_group) >= 2 and len(set(slots_in_group)) < len(slots_in_group):
                conflict_hits += 1
    max_conflicts = len(conflicts) if conflicts else 1
    conflict_score = 1.0 - (conflict_hits / max_conflicts)

    slot_counts = Counter(a["time_slot_id"] for a in assignments)
    counts = list(slot_counts.values())
    if len(counts) > 1:
        mean_load = sum(counts) / len(counts)
        variance = sum((c - mean_load) ** 2 for c in counts) / len(counts)
        std_dev = math.sqrt(variance)
        mean_all = len(assignments) / 8
        balance = max(0.0, 1.0 - std_dev / mean_all) if mean_all > 0 else 0.0
    else:
        balance = 0.5

    final = (
        eff["room_util"]      * room_util
        + eff["faculty_sat"]    * fac_sat
        + eff["conflict_avoid"] * conflict_score
        + eff["load_balance"]   * balance
    )
    return round(final, 4)


def main():
    schedule_path = sys.argv[1] if len(sys.argv) > 1 else "/opt/scheduler/schedule.json"
    try:
        eff = load_effective_policy()
        score = score_schedule(schedule_path)
        print(f"Score: {score:.4f} / threshold {eff['pass_score']:.4f}")
        sys.exit(0 if score >= eff["pass_score"] else 1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
