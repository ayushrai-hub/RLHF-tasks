"""Verifier for the offline carillon session planner."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
from datetime import datetime, timedelta, timezone
from itertools import combinations
from pathlib import Path


PUBLIC_INPUT = Path("/app/input/august_rota_requests.json")
PLANNER = Path("/app/carillon-planner")
PUBLIC_SHA256 = "729e01886d250a501e8eb6a8bcf5fdd0d77962cc9e59a86f012547c86f671224"
TIERS = {"novice": 0, "competent": 1, "experienced": 2, "conductor": 3}


def _minutes(iso: str) -> int:
    dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() // 60)


def _overlap(a: dict, b: dict) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def _duration(p: dict) -> int:
    return _minutes(p["end"]) - _minutes(p["start"])


def _proposal_ringers(p: dict) -> list[str]:
    return [a["ringer"] for a in sorted(p["assignments"], key=lambda x: x["bell"])]


def _internal_conflict(a: dict, b: dict) -> bool:
    shared = set(_proposal_ringers(a)) & set(_proposal_ringers(b))
    if a["tower"] == b["tower"] and _overlap(a, b):
        return True
    if shared and _overlap(a, b):
        return True
    if shared:
        gap = max(_minutes(a["start"]), _minutes(b["start"])) - min(
            _minutes(a["end"]), _minutes(b["end"])
        )
        if gap < 30:
            return True
    return False


def _within_minute_caps(data: dict, items: list[dict]) -> bool:
    towers = {t["id"]: t for t in data["towers"]}
    ringers = {r["name"]: r for r in data["ringers"]}
    tower_minutes = {tower_id: 0 for tower_id in towers}
    ringer_minutes = {name: 0 for name in ringers}
    for p in items:
        length = _duration(p)
        tower_minutes[p["tower"]] += length
        for name in set(_proposal_ringers(p)):
            ringer_minutes[name] += length
    return all(
        used <= towers[tower_id]["max_minutes"]
        for tower_id, used in tower_minutes.items()
    ) and all(
        used <= ringers[name]["max_minutes"]
        for name, used in ringer_minutes.items()
    )


def _first_usability_reason(data: dict, p: dict) -> str | None:
    towers = {t["id"]: t for t in data["towers"]}
    ringers = {r["name"]: r for r in data["ringers"]}
    tower = towers.get(p["tower"])
    if tower is None:
        return "tower_unknown"
    if p["method"] not in tower["methods"]:
        return "method_unsupported"
    if p["end"] <= p["start"]:
        return "bad_interval"
    bells = [a.get("bell") for a in p["assignments"]]
    if sorted(bells) != list(range(1, tower["bells"] + 1)):
        return "bad_assignments"
    names = [a.get("ringer") for a in p["assignments"]]
    if any(name not in ringers for name in names):
        return "ringer_unknown"
    if len(set(names)) != len(names):
        return "duplicate_ringer"
    for assignment in p["assignments"]:
        bell = assignment["bell"]
        tier = ringers[assignment["ringer"]]["tier"]
        needed = "novice"
        if bell == tower["bells"]:
            needed = "experienced"
        elif bell > tower["bells"] // 2:
            needed = "competent"
        if TIERS[tier] < TIERS[needed]:
            return "tier_mismatch"
    for row in data["maintenance"]:
        if row["kind"] == "hard" and row["tower"] == p["tower"] and _overlap(row, p):
            return "maintenance"
    assigned = set(names)
    for session in data["existing_sessions"]:
        if session["status"] != "scheduled" or not _overlap(session, p):
            continue
        if session["tower"] == p["tower"]:
            return "tower_busy"
        if assigned & set(session["ringers"]):
            return "ringer_busy"
    return None


def _better(candidate: list[dict], incumbent: list[dict] | None) -> bool:
    if incumbent is None:
        return True
    c_ids = ",".join(sorted(p["id"] for p in candidate))
    i_ids = ",".join(sorted(p["id"] for p in incumbent))
    c_key = (sum(p["score"] for p in candidate), len(candidate), -sum(_duration(p) for p in candidate))
    i_key = (sum(p["score"] for p in incumbent), len(incumbent), -sum(_duration(p) for p in incumbent))
    return c_key > i_key or (c_key == i_key and c_ids < i_ids)


def _compatible(items: list[dict]) -> bool:
    return all(not _internal_conflict(a, b) for a, b in combinations(items, 2))


def _feasible(data: dict, items: list[dict]) -> bool:
    return _compatible(items) and _within_minute_caps(data, items)


def expected_plan(data: dict) -> dict:
    usable = []
    rejected_by_rule = {}
    for p in data["proposals"]:
        reason = _first_usability_reason(data, p)
        if reason is None:
            usable.append(p)
        else:
            rejected_by_rule[p["id"]] = reason

    mandatory = [p for p in usable if p["mandatory"]]
    if not _feasible(data, mandatory):
        selected: list[dict] = []
        rejected = []
        for p in data["proposals"]:
            if p["id"] in rejected_by_rule:
                rejected.append({"id": p["id"], "reason": rejected_by_rule[p["id"]]})
            elif p["mandatory"]:
                rejected.append({"id": p["id"], "reason": "mandatory_conflict"})
            else:
                rejected.append({"id": p["id"], "reason": "blocked_by_mandatory_conflict"})
        return {"status": "infeasible", "selected": selected, "rejected": rejected, "total_score": 0}

    optional = [p for p in usable if not p["mandatory"]]
    best: list[dict] | None = None
    for mask in range(1 << len(optional)):
        trial = mandatory + [optional[i] for i in range(len(optional)) if mask & (1 << i)]
        if _feasible(data, trial) and _better(trial, best):
            best = trial
    chosen = sorted(best or [], key=lambda p: p["id"])
    chosen_ids = {p["id"] for p in chosen}
    rejected = []
    for p in data["proposals"]:
        reason = rejected_by_rule.get(p["id"])
        if reason is not None:
            rejected.append({"id": p["id"], "reason": reason})
        elif p["id"] not in chosen_ids:
            rejected.append({"id": p["id"], "reason": "conflicts_with_selected"})
    return {
        "status": "ok",
        "selected": [
            {
                "id": p["id"],
                "tower": p["tower"],
                "start": p["start"],
                "end": p["end"],
                "score": p["score"],
                "ringers": _proposal_ringers(p),
            }
            for p in chosen
        ],
        "rejected": rejected,
        "total_score": sum(p["score"] for p in chosen),
    }


def _run_planner(data: dict, tmp_path: Path) -> dict:
    in_path = tmp_path / "input.json"
    out_path = tmp_path / "out.json"
    in_path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    result = subprocess.run(
        [str(PLANNER), str(in_path), str(out_path)],
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    assert out_path.exists(), "planner did not create the requested output file"
    with out_path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _load_public() -> dict:
    with PUBLIC_INPUT.open(encoding="utf-8") as handle:
        return json.load(handle)


def _base_variant() -> dict:
    return {
        "towers": [
            {"id": "alpha", "bells": 4, "methods": ["PlainBob", "Grandsire"], "max_minutes": 240},
            {"id": "beta", "bells": 4, "methods": ["PlainBob"], "max_minutes": 240},
        ],
        "ringers": [
            {"name": "ann", "tier": "conductor", "max_minutes": 240},
            {"name": "bo", "tier": "experienced", "max_minutes": 240},
            {"name": "cam", "tier": "competent", "max_minutes": 240},
            {"name": "dee", "tier": "novice", "max_minutes": 240},
            {"name": "eli", "tier": "experienced", "max_minutes": 240},
            {"name": "fay", "tier": "competent", "max_minutes": 240},
        ],
        "existing_sessions": [],
        "maintenance": [],
        "proposals": [],
    }


def _p(pid: str, tower: str, start: str, end: str, score: int, names: list[str], mandatory: bool = False, method: str = "PlainBob") -> dict:
    return {
        "id": pid,
        "tower": tower,
        "method": method,
        "start": start,
        "end": end,
        "score": score,
        "mandatory": mandatory,
        "assignments": [{"bell": i + 1, "ringer": name} for i, name in enumerate(names)],
    }


def _iso_at(day: str, minute_offset: int) -> str:
    base = datetime.strptime(f"{day}T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return (base + timedelta(minutes=minute_offset)).strftime("%Y-%m-%dT%H:%M:%SZ")


def assert_matches_reference(data: dict, tmp_path: Path) -> None:
    """Run the submitted planner and compare it with the rule-based reference result."""
    assert _run_planner(data, tmp_path) == expected_plan(data)


def test_executable_and_sample_rota_integrity():
    """Verify the required executable exists and the sample rota file was not changed."""
    assert PLANNER.exists(), "/app/carillon-planner is missing"
    assert os.access(PLANNER, os.X_OK), "/app/carillon-planner is not executable"
    assert stat.S_ISREG(PLANNER.stat().st_mode)
    digest = hashlib.sha256(PUBLIC_INPUT.read_bytes()).hexdigest()
    assert digest == PUBLIC_SHA256


def test_sample_rota_requires_global_choice(tmp_path):
    """The sample rota should select the better compatible set, not the single highest score proposal."""
    data = _load_public()
    actual = _run_planner(data, tmp_path)
    assert actual == expected_plan(data)
    assert [row["id"] for row in actual["selected"]] == ["A", "C", "D", "M1"]
    assert actual["total_score"] == 162


def test_rejection_reasons_follow_rota_policy_order(tmp_path):
    """Several bad rota requests exercise each rejection reason and its precedence."""
    data = _base_variant()
    good = ["dee", "cam", "bo", "ann"]
    data["existing_sessions"] = [
        {"id": "busy-tower", "tower": "alpha", "start": "2026-09-01T15:00:00Z", "end": "2026-09-01T16:00:00Z", "status": "scheduled", "ringers": good},
        {"id": "busy-ringer", "tower": "beta", "start": "2026-09-01T17:00:00Z", "end": "2026-09-01T18:00:00Z", "status": "scheduled", "ringers": ["eli"]},
    ]
    data["maintenance"] = [{"tower": "alpha", "start": "2026-09-01T13:00:00Z", "end": "2026-09-01T14:00:00Z", "kind": "hard"}]
    data["proposals"] = [
        _p("tower", "missing", "2026-09-01T08:00:00Z", "2026-09-01T09:00:00Z", 1, good, method="Nope"),
        _p("method", "beta", "2026-09-01T08:00:00Z", "2026-09-01T09:00:00Z", 1, good, method="Grandsire"),
        _p("interval", "alpha", "2026-09-01T10:00:00Z", "2026-09-01T10:00:00Z", 1, good),
        _p("bells", "alpha", "2026-09-01T10:00:00Z", "2026-09-01T11:00:00Z", 1, ["dee", "cam", "bo"]),
        _p("unknown-ringer", "alpha", "2026-09-01T10:00:00Z", "2026-09-01T11:00:00Z", 1, ["dee", "cam", "bo", "zed"]),
        _p("dupe-ringer", "alpha", "2026-09-01T10:00:00Z", "2026-09-01T11:00:00Z", 1, ["dee", "cam", "bo", "bo"]),
        _p("tier", "alpha", "2026-09-01T10:00:00Z", "2026-09-01T11:00:00Z", 1, ["dee", "cam", "bo", "fay"]),
        _p("maint", "alpha", "2026-09-01T13:10:00Z", "2026-09-01T13:50:00Z", 1, good),
        _p("tower-busy", "alpha", "2026-09-01T15:10:00Z", "2026-09-01T15:50:00Z", 1, good),
        _p("ringer-busy", "alpha", "2026-09-01T17:10:00Z", "2026-09-01T17:50:00Z", 1, ["dee", "cam", "eli", "ann"]),
        _p("ok", "alpha", "2026-09-01T19:00:00Z", "2026-09-01T20:00:00Z", 5, good),
    ]
    assert_matches_reference(data, tmp_path)


def test_tie_breaks_compare_the_complete_rota(tmp_path):
    """Equivalent rota choices are resolved by score, count, duration, and selected ids."""
    data = _base_variant()
    names = ["dee", "cam", "bo", "ann"]
    data["proposals"] = [
        _p("aa", "alpha", "2026-09-02T08:00:00Z", "2026-09-02T10:00:00Z", 50, names),
        _p("ab", "alpha", "2026-09-02T10:30:00Z", "2026-09-02T11:30:00Z", 30, names),
        _p("ac", "alpha", "2026-09-02T12:00:00Z", "2026-09-02T13:00:00Z", 20, names),
        _p("ba", "beta", "2026-09-02T08:00:00Z", "2026-09-02T09:00:00Z", 45, ["dee", "fay", "eli", "ann"]),
        _p("bb", "beta", "2026-09-02T09:30:00Z", "2026-09-02T10:30:00Z", 35, ["dee", "fay", "eli", "ann"]),
        _p("bc", "beta", "2026-09-02T11:00:00Z", "2026-09-02T12:00:00Z", 20, ["dee", "fay", "eli", "ann"]),
    ]
    assert_matches_reference(data, tmp_path)


def test_conflicting_mandatory_sessions_make_rota_infeasible(tmp_path):
    """Two usable mandatory proposals that conflict should produce the documented infeasible output."""
    data = _base_variant()
    names = ["dee", "cam", "bo", "ann"]
    data["proposals"] = [
        _p("m1", "alpha", "2026-09-03T08:00:00Z", "2026-09-03T09:00:00Z", 20, names, mandatory=True),
        _p("m2", "alpha", "2026-09-03T08:30:00Z", "2026-09-03T09:30:00Z", 25, names, mandatory=True),
        _p("o1", "beta", "2026-09-03T10:00:00Z", "2026-09-03T11:00:00Z", 90, ["dee", "fay", "eli", "ann"]),
        _p("bad", "missing", "2026-09-03T12:00:00Z", "2026-09-03T13:00:00Z", 90, names),
    ]
    assert_matches_reference(data, tmp_path)


def test_rest_gap_blocks_back_to_back_shared_ringers(tmp_path):
    """A shared ringer must have 30 minutes of rest even when selected intervals do not overlap."""
    data = _base_variant()
    data["proposals"] = [
        _p("first", "alpha", "2026-09-04T08:00:00Z", "2026-09-04T09:00:00Z", 50, ["dee", "cam", "bo", "ann"]),
        _p("too-soon", "beta", "2026-09-04T09:20:00Z", "2026-09-04T10:20:00Z", 51, ["dee", "fay", "eli", "ann"]),
        _p("after-rest", "beta", "2026-09-04T09:30:00Z", "2026-09-04T10:30:00Z", 50, ["dee", "fay", "eli", "ann"]),
    ]
    assert_matches_reference(data, tmp_path)


def test_minute_caps_can_outweigh_a_high_score_session(tmp_path):
    """Tower and ringer minute caps should be applied to the complete selected plan."""
    data = _base_variant()
    data["towers"][0]["max_minutes"] = 120
    for ringer in data["ringers"]:
        if ringer["name"] in {"ann", "bo", "cam", "dee"}:
            ringer["max_minutes"] = 120
    names = ["dee", "cam", "bo", "ann"]
    data["proposals"] = [
        _p("long", "alpha", "2026-09-05T08:00:00Z", "2026-09-05T10:30:00Z", 80, names),
        _p("s1", "alpha", "2026-09-05T08:00:00Z", "2026-09-05T09:00:00Z", 45, names),
        _p("s2", "alpha", "2026-09-05T09:30:00Z", "2026-09-05T10:30:00Z", 45, names),
        _p("b1", "beta", "2026-09-05T11:00:00Z", "2026-09-05T12:00:00Z", 10, ["dee", "fay", "eli", "ann"]),
    ]
    actual = _run_planner(data, tmp_path)
    assert actual == expected_plan(data)
    assert [row["id"] for row in actual["selected"]] == ["s1", "s2"]
    assert actual["total_score"] == 90


def test_large_rota_respects_minute_caps_exactly(tmp_path):
    """A larger rota chooses the best capped combination instead of the biggest single session."""
    data = _base_variant()
    data["towers"][0]["max_minutes"] = 300
    names = ["dee", "cam", "bo", "ann"]
    for ringer in data["ringers"]:
        if ringer["name"] in names:
            ringer["max_minutes"] = 300

    specs = [("full-afternoon", 300, 120)]
    specs.extend((f"k{i:02d}", 60, 31) for i in range(6))
    specs.extend((f"m{i:02d}", 45, 22) for i in range(10))
    specs.extend((f"f{i:02d}", 30, 5) for i in range(17))

    start_minute = 8 * 60
    proposals = []
    for pid, length, score in specs:
        proposals.append(
            _p(
                pid,
                "alpha",
                _iso_at("2026-09-20", start_minute),
                _iso_at("2026-09-20", start_minute + length),
                score,
                names,
            )
        )
        start_minute += length + 30
    data["proposals"] = proposals

    actual = _run_planner(data, tmp_path)
    chosen_ids = [f"k{i:02d}" for i in range(5)]
    chosen = sorted([p for p in proposals if p["id"] in set(chosen_ids)], key=lambda p: p["id"])
    expected = {
        "status": "ok",
        "selected": [
            {
                "id": p["id"],
                "tower": p["tower"],
                "start": p["start"],
                "end": p["end"],
                "score": p["score"],
                "ringers": _proposal_ringers(p),
            }
            for p in chosen
        ],
        "rejected": [
            {"id": p["id"], "reason": "conflicts_with_selected"}
            for p in proposals
            if p["id"] not in set(chosen_ids)
        ],
        "total_score": 155,
    }
    assert actual == expected


def test_mandatory_sessions_can_exceed_the_tower_cap(tmp_path):
    """Mandatory proposals that only violate minute caps should still make the request infeasible."""
    data = _base_variant()
    data["towers"][0]["max_minutes"] = 100
    names = ["dee", "cam", "bo", "ann"]
    data["proposals"] = [
        _p("m1", "alpha", "2026-09-06T08:00:00Z", "2026-09-06T09:00:00Z", 20, names, mandatory=True),
        _p("m2", "alpha", "2026-09-06T09:30:00Z", "2026-09-06T10:30:00Z", 25, names, mandatory=True),
        _p("o1", "beta", "2026-09-06T11:00:00Z", "2026-09-06T12:00:00Z", 50, ["dee", "fay", "eli", "ann"]),
    ]
    actual = _run_planner(data, tmp_path)
    assert actual == expected_plan(data)
    assert actual["status"] == "infeasible"
    assert actual["selected"] == []


def test_empty_input_arrays_are_valid(tmp_path):
    """Empty input arrays should produce a valid empty ok plan."""
    data = {
        "towers": [],
        "ringers": [],
        "existing_sessions": [],
        "maintenance": [],
        "proposals": [],
    }
    actual = _run_planner(data, tmp_path)
    assert actual == {
        "status": "ok",
        "selected": [],
        "rejected": [],
        "total_score": 0,
    }


def test_rota_variations_with_different_caps_and_maintenance(tmp_path):
    """Several rota variations cover ordering, tower limits, maintenance, and score patterns."""
    for seed in range(16):
        data = _base_variant()
        data["towers"][0]["max_minutes"] = 170 if seed % 5 == 0 else 240
        data["ringers"][0]["max_minutes"] = 170 if seed % 7 == 0 else 240
        data["maintenance"] = [
            {"tower": "beta", "start": f"2026-09-{10 + seed:02d}T12:00:00Z", "end": f"2026-09-{10 + seed:02d}T12:40:00Z", "kind": "hard" if seed % 3 == 0 else "soft"}
        ]
        day = f"2026-09-{10 + seed:02d}"
        alpha = ["dee", "cam", "bo", "ann"]
        beta = ["dee", "fay", "eli", "ann"]
        data["proposals"] = [
            _p(f"x{seed}", "alpha", f"{day}T08:00:00Z", f"{day}T09:00:00Z", 30 + seed, alpha, mandatory=seed % 4 == 0),
            _p(f"y{seed}", "alpha", f"{day}T09:30:00Z", f"{day}T10:20:00Z", 38, alpha),
            _p(f"z{seed}", "alpha", f"{day}T10:50:00Z", f"{day}T11:40:00Z", 39, alpha),
            _p(f"long{seed}", "alpha", f"{day}T09:20:00Z", f"{day}T11:50:00Z", 70, alpha),
            _p(f"b{seed}", "beta", f"{day}T12:10:00Z", f"{day}T13:00:00Z", 44, beta),
            _p(f"c{seed}", "beta", f"{day}T13:30:00Z", f"{day}T14:20:00Z", 43, beta),
        ]
        assert_matches_reference(data, tmp_path)
