import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

APP = Path("/app")
ENV = APP / "environment"
OUT = APP / "output"
REPORT = OUT / "audit_report.json"
LAYOUT = json.loads((ENV / "manifest" / "layout.json").read_text())
HEX64 = re.compile(r"[0-9a-f]{64}")
JOURNAL_NAMES = ("batch.json", "batch.replay.json", "batch.shadow.json", "batch.spill.json")


def _read_rows(path):
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    return value if isinstance(value, list) else []


def _state_dir(profile):
    return OUT / "state" / profile


def _fixtures(profile):
    rows = []
    for path in sorted((ENV / "fixtures" / f"{profile}_rules").glob("*.json")):
        rows.extend(_read_rows(path))
    return rows


def _journal_rows(profile):
    rows = []
    for name in JOURNAL_NAMES:
        rows.extend(_read_rows(_state_dir(profile) / name))
    return rows or _fixtures(profile)


def _canonical_rows(profile):
    chosen = {}
    for source_index, rec in enumerate(_journal_rows(profile)):
        owner = rec.get("profile")
        if owner not in (None, "", profile):
            continue
        key = (rec["seq"], rec["run_id"], rec["phase"], rec["rule_id"], rec["action"])
        rank = (rec["epoch"], source_index)
        prior = chosen.get(key)
        if prior is None or rank >= prior[0]:
            chosen[key] = (rank, rec)
    return sorted(
        (item[1] for item in chosen.values()),
        key=lambda r: (r["seq"], r["run_id"], r["phase"], r["rule_id"]),
    )


def _segments(rows, run_id, phase):
    return [r for r in rows if r["run_id"] == run_id and r["phase"] == phase]


def _rules(records):
    latest = {}
    for rec in sorted(records, key=lambda r: (r["seq"], r["rule_id"])):
        latest[rec["rule_id"]] = {
            "rule_id": rec["rule_id"],
            "priority": rec["priority"],
            "epoch": rec["epoch"],
            "mark": rec["mark"],
        }
    return [latest[rid] for rid in sorted(latest)]


def _tree_hash(rules):
    payload = [
        {"rule_id": r["rule_id"], "priority": r["priority"], "epoch": r["epoch"]}
        for r in sorted(rules, key=lambda r: r["rule_id"])
    ]
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def _observed_hash(rule):
    payload = {
        "rule_id": rule["rule_id"],
        "priority": rule["priority"],
        "epoch": rule["epoch"],
        "mark": rule["mark"],
    }
    return hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).hexdigest()


def _profile_runs(profile):
    import tomllib

    data = tomllib.loads((ENV / "profiles" / f"{profile}.toml").read_text())
    return list(data["runs"])


def _persisted_epoch(profile):
    try:
        return json.loads((_state_dir(profile) / "epoch.json").read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _expected_report(profile):
    rows = _canonical_rows(profile)
    layout = LAYOUT[profile]
    persisted = _persisted_epoch(profile)
    max_epoch = max([layout["epoch"], persisted.get("epoch", 0), *(r["epoch"] for r in rows)], default=layout["epoch"])
    counter = max(layout["counter"], persisted.get("counter", 0), len(rows))
    runs = []
    entries = []
    checkpoints = []
    for run_id in _profile_runs(profile):
        for phase in ("apply", "settle"):
            segment = _segments(rows, run_id, phase)
            rules = _rules(segment)
            tree = _tree_hash(rules)
            runs.append({"run_id": run_id, "phase": phase, "tree_hash": tree})
            seqs = [r["seq"] for r in segment]
            epochs = [r["epoch"] for r in segment]
            checkpoints.append(
                {
                    "run_id": run_id,
                    "phase": phase,
                    "first_seq": min(seqs, default=0),
                    "last_seq": max(seqs, default=0),
                    "record_count": len(segment),
                    "epoch_floor": min(epochs, default=0),
                    "epoch_ceil": max(epochs, default=0),
                    "tree_hash": tree,
                }
            )
            for rule in rules:
                entries.append(
                    {
                        "rule_id": rule["rule_id"],
                        "action": phase,
                        "epoch": rule["epoch"],
                        "observed_hash": _observed_hash(rule),
                    }
                )
    runs.sort(key=lambda r: (r["run_id"], r["phase"]))
    entries.sort(key=lambda e: (e["rule_id"], e["epoch"], e["action"]))
    checkpoints.sort(key=lambda c: (c["run_id"], c["phase"]))
    return {
        "profile": profile,
        "epoch": max_epoch,
        "counter": counter,
        "runs": runs,
        "entries": entries,
        "checkpoints": checkpoints,
    }


def _run_audit(profile, reset=True):
    if reset:
        shutil.rmtree(OUT, ignore_errors=True)
    subprocess.run(
        ["go", "run", "/app/environment/cmd/nfrd", "audit", "--profile", profile],
        cwd=ENV,
        check=True,
        text=True,
        capture_output=True,
        timeout=120,
    )
    return json.loads(REPORT.read_text())


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, separators=(",", ":")) + "\n")


def _assert_epoch_seal(profile, report):
    seal = json.loads((_state_dir(profile) / "epoch.json").read_text())
    assert seal["epoch"] == report["epoch"]
    assert seal["counter"] == report["counter"]
    assert isinstance(seal.get("tag", ""), str)


def _assert_report_shape(report):
    assert set(report) == {"profile", "epoch", "counter", "runs", "entries", "checkpoints"}
    assert isinstance(report["profile"], str)
    assert isinstance(report["epoch"], int)
    assert isinstance(report["counter"], int)
    assert isinstance(report["runs"], list)
    assert isinstance(report["entries"], list)
    assert isinstance(report["checkpoints"], list)
    for run in report["runs"]:
        assert set(run) == {"run_id", "phase", "tree_hash"}
        assert run["phase"] in {"apply", "settle"}
        assert HEX64.fullmatch(run["tree_hash"])
    for entry in report["entries"]:
        assert set(entry) == {"rule_id", "action", "epoch", "observed_hash"}
        assert entry["action"] in {"apply", "settle"}
        assert isinstance(entry["epoch"], int)
        assert HEX64.fullmatch(entry["observed_hash"])
    for point in report["checkpoints"]:
        assert set(point) == {
            "run_id",
            "phase",
            "first_seq",
            "last_seq",
            "record_count",
            "epoch_floor",
            "epoch_ceil",
            "tree_hash",
        }
        assert point["phase"] in {"apply", "settle"}
        assert point["first_seq"] <= point["last_seq"] or not point["record_count"]
        assert point["epoch_floor"] <= point["epoch_ceil"] or not point["record_count"]
        assert HEX64.fullmatch(point["tree_hash"])


def _assert_no_boolean_verdicts(value):
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = key.lower()
            if lowered.endswith(("_ok", "_valid", "_green", "_passes")):
                raise AssertionError(key)
            if isinstance(child, bool):
                raise AssertionError(key)
            _assert_no_boolean_verdicts(child)
    elif isinstance(value, list):
        for child in value:
            _assert_no_boolean_verdicts(child)


def test_replay_checkpoint_contract():
    """Gate audit rebuilds phase-scoped runs and checkpoint spans from duplicated journal residue."""
    report = _run_audit("gate")
    _assert_report_shape(report)
    _assert_no_boolean_verdicts(report)
    assert report == _expected_report("gate")
    assert any(
        point["record_count"] > 0 and point["first_seq"] < point["last_seq"]
        for point in report["checkpoints"]
    )


def test_corrupt_primary_batch_uses_replay_companions():
    """Depot audit survives a malformed primary batch and still folds readable companion journals."""
    first = _run_audit("depot")
    state = _state_dir("depot")
    (state / "batch.json").write_text("[")
    rows = _fixtures("depot")
    extra = dict(
        rows[0],
        seq=9,
        epoch=7,
        priority=333,
        mark=0.77,
        phase="settle",
    )
    _write_json(state / "batch.shadow.json", [extra, rows[0], rows[-1]])
    _write_json(state / "epoch.json", {"epoch": 2, "counter": 99, "tag": "stale-depot"})
    second = _run_audit("depot", reset=False)
    assert first != second
    assert second == _expected_report("depot")


def test_spill_rows_are_ordered_before_hashing():
    """Yard rerun incorporates out-of-order spill rows without letting append order change hashes."""
    _run_audit("yard")
    rows = _fixtures("yard")
    spill = [
        dict(rows[1], seq=12, epoch=4, priority=121, mark=0.52, phase="settle"),
        dict(rows[0], seq=11, epoch=3, priority=88, mark=0.31, phase="apply"),
        dict(rows[0], seq=1, epoch=1, priority=90, mark=0.33, phase="apply"),
    ]
    _write_json(_state_dir("yard") / "batch.spill.json", spill)
    report = _run_audit("yard", reset=False)
    expected = _expected_report("yard")
    assert report == expected
    assert report["runs"] == _run_audit("yard", reset=False)["runs"]


def test_interleaved_profile_owners_and_epoch_seals_are_namespaced():
    """Interleaved residue with explicit owners is ignored unless it belongs to the active profile."""
    gate = _run_audit("gate")
    yard = _run_audit("yard", reset=False)
    gate_expected = _expected_report("gate")
    yard_expected = _expected_report("yard")
    state = _state_dir("yard")
    rows = _fixtures("yard")
    alien = dict(
        rows[0],
        profile="gate",
        seq=17,
        epoch=44,
        priority=999,
        mark=0.99,
        phase="settle",
    )
    owned = dict(
        rows[1],
        profile="yard",
        seq=18,
        epoch=6,
        priority=118,
        mark=0.39,
        phase="settle",
    )
    _write_json(state / "batch.shadow.json", [alien, owned])
    rerun = _run_audit("yard", reset=False)
    assert gate == gate_expected
    assert yard == yard_expected
    assert rerun == _expected_report("yard")
    _assert_epoch_seal("yard", rerun)
    assert rerun["epoch"] == 6
    assert all(entry["epoch"] != 44 for entry in rerun["entries"])


def test_laneprobe_green_does_not_prevent_reseal_from_new_journal_rows():
    """A green readiness probe remains advisory while audit reseals from later journal evidence."""
    subprocess.run(
        ["go", "run", "/app/environment/cmd/laneprobe", "yard"],
        cwd=ENV,
        check=True,
        text=True,
        capture_output=True,
        timeout=60,
    )
    rows = _fixtures("yard")
    _write_json(
        _state_dir("yard") / "epoch.json",
        {"epoch": 1, "counter": 1, "tag": "old-yard"},
    )
    _write_json(
        _state_dir("yard") / "batch.spill.json",
        [
            dict(rows[0], seq=21, epoch=7, priority=131, mark=0.45, phase="apply"),
            dict(rows[1], seq=22, epoch=8, priority=119, mark=0.41, phase="settle"),
        ],
    )
    report = _run_audit("yard", reset=False)
    probe = json.loads((_state_dir("yard") / "lane.json").read_text())
    assert set(probe) >= {"state", "tag"}
    assert report == _expected_report("yard")
    _assert_epoch_seal("yard", report)
    assert report["epoch"] == 8
    assert report["counter"] >= len(_canonical_rows("yard"))


def test_duplicate_replay_is_idempotent():
    """Repeated depot audit keeps the same canonical rows even after replay files are duplicated."""
    first = _run_audit("depot")
    state = _state_dir("depot")
    replay = _read_rows(state / "batch.replay.json")
    extra = dict(
        replay[0],
        seq=10,
        epoch=8,
        priority=305,
        mark=0.8,
        phase="apply",
    )
    _write_json(state / "batch.spill.json", list(reversed(replay)) + replay + [extra])
    second = _run_audit("depot", reset=False)
    third = _run_audit("depot", reset=False)
    assert first != second
    assert second == _expected_report("depot")
    assert second == third


def test_primary_loss_companion_rows_keep_empty_phase_deterministic():
    """A malformed primary with only apply companions still emits deterministic empty settle checkpoints."""
    _run_audit("yard")
    state = _state_dir("yard")
    rows = [r for r in _canonical_rows("yard") if r["phase"] != "settle"]
    (state / "batch.json").write_text("{")
    _write_json(state / "batch.replay.json", rows)
    _write_json(
        state / "batch.shadow.json",
        [dict(rows[0], profile="gate", seq=30, epoch=12, priority=500)],
    )
    _write_json(state / "batch.spill.json", list(reversed(rows)))
    report = _run_audit("yard", reset=False)
    expected = _expected_report("yard")
    assert report == expected
    _assert_epoch_seal("yard", report)
    empty_points = [p for p in report["checkpoints"] if p["phase"] == "settle"]
    assert empty_points == [
        {
            "run_id": "run-a",
            "phase": "settle",
            "first_seq": 0,
            "last_seq": 0,
            "record_count": 0,
            "epoch_floor": 0,
            "epoch_ceil": 0,
            "tree_hash": _tree_hash([]),
        }
    ]
