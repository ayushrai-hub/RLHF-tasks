"""Milestone 2 verifier: reconcile and disposition the warm-up plan.

Re-runs the agent's /app/plan.pl reconcile on the bundled and held-out files, deep-comparing
/app/out/reconcile.json to the reference. Crafted cases pin the disposition PRECEDENCE
(PIN > QUARANTINE > COLD > WARM) and, crucially, the POLICY VALUES that the chronicle settles
only through its amendment chain: the pin marker is the SECOND character equal to 0 (an older
marker 9 is declined), the quarantined zones are Q and X (Z was decommissioned), the cold
threshold is 90000, and H is the only hot zone. A solver that lifts a superseded value gets the
wrong disposition and fails.
"""
import base64
import json
import os
import subprocess

import reference as R

DAT = "/app/warmcache.dat"
OUT = "/app/out"
SRC = "/app/plan.pl"


def _run(stage, timeout=60):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, stage + ".json")
    if os.path.exists(p):
        os.remove(p)
    proc = subprocess.run(["perl", SRC, stage], capture_output=True, text=True, timeout=timeout)
    assert os.path.exists(p), f"{stage}.json was not written; perl stderr: {proc.stderr[-400:]}"
    with open(p) as f:
        return json.load(f)


def _norm(d):
    return json.loads(json.dumps(d))


def _frame(seq, rec):
    return "%d %s %d" % (seq, base64.b64encode(rec).decode(), R.cksum_crc(rec))


def _write(objs):
    """objs: list of (key, weight, prereqs). Emits an OBJ and a HIT frame for each."""
    lines, s = [], 1
    for key, _w, pre in objs:
        lines.append(_frame(s, ("OBJ %s %s" % (key, pre)).encode()))
        s += 1
    for key, w, _pre in objs:
        lines.append(_frame(s, ("HIT %s %d" % (key, w)).encode()))
        s += 1
    return "".join(x + "\n" for x in lines)


def _disp(out):
    return {k: d for k, d in out["disposition"]}


def _drive(objs):
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(_write(objs))
        out = _run("reconcile")
        assert _norm(out) == _norm(R.stage2_reconcile(open(DAT).read()))
        return out
    finally:
        open(DAT, "w").write(backup)


def test_reconcile_shape():
    """reconcile.json is a JSON object with joined, disposition, resolvable, plan and dangling."""
    out = _run("reconcile")
    assert set(out) == {"joined", "disposition", "resolvable", "plan", "dangling"}
    assert isinstance(out["resolvable"], bool)


def test_reconcile_matches_reference_on_bundled():
    """The reconcile of the bundled descriptor file equals the independent reference exactly."""
    lock = open(DAT).read()
    assert _run("reconcile") == _norm(R.stage2_reconcile(lock))


def test_join_is_inner_not_outer():
    """Only keys with BOTH an OBJ and a HIT are joined and dispositioned (inner join)."""
    text = _frame(1, b"OBJ A5A -") + "\n" + _frame(2, b"OBJ A6B -") + "\n" + _frame(3, b"HIT A5A 100000") + "\n"
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(text)
        out = _run("reconcile")
        assert out["joined"] == ["A5A"], "A6B has no HIT and must not be joined"
    finally:
        open(DAT, "w").write(backup)


def test_pin_overrides_quarantine():
    """A pinned object (second char is the pin marker) in a quarantined zone is warmed; a
    non-pinned object in the same zone is quarantined and excluded."""
    out = _drive([("Q0A", 5, "-"), ("Q4B", 5, "-"), ("A5C", 100000, "-")])
    d = _disp(out)
    assert d["Q0A"] == "PIN" and "Q0A" in out["plan"]
    assert d["Q4B"] == "QUARANTINE" and "Q4B" not in out["plan"]


def test_pin_overrides_cold():
    """A pinned object with a cold weight is warmed; a non-pinned cold object is excluded."""
    out = _drive([("D0A", 5, "-"), ("D5B", 5, "-")])
    d = _disp(out)
    assert d["D0A"] == "PIN" and "D0A" in out["plan"]
    assert d["D5B"] == "COLD" and "D5B" not in out["plan"]


def test_cold_excluded_unless_hot_zone():
    """A cold-weight object is excluded, but a cold-weight object in a hot zone stays warmed."""
    out = _drive([("N5A", 5, "-"), ("H5B", 5, "-")])
    d = _disp(out)
    assert d["N5A"] == "COLD" and "N5A" not in out["plan"]
    assert d["H5B"] == "WARM" and "H5B" in out["plan"]


def test_pin_marker_is_current_not_superseded():
    """The pin marker is the second character 0 (the current value); the superseded marker 9 does
    NOT pin. A cold-weight key A9x must be COLD, while A0x is PIN."""
    out = _drive([("A9A", 5, "-"), ("A0B", 5, "-")])
    d = _disp(out)
    assert d["A9A"] == "COLD", "second char 9 is the OLD pin marker and must not pin"
    assert d["A0B"] == "PIN"


def test_quarantine_zone_set_is_current():
    """The quarantined zones are Q and X; zone Z (decommissioned) is NOT quarantined, so a warm
    Z object is WARM and an X object is QUARANTINE."""
    out = _drive([("Z5A", 100000, "-"), ("X5B", 100000, "-")])
    d = _disp(out)
    assert d["Z5A"] == "WARM", "zone Z was decommissioned and is not quarantined"
    assert d["X5B"] == "QUARANTINE"


def test_plan_is_topological_c_locale():
    """The warm-up plan orders warmed prerequisites before dependents, ties by C-locale key."""
    out = _drive([("A5C", 100000, "A5A,A5B"), ("A5A", 100000, "-"), ("A5B", 100000, "-")])
    assert out["plan"] == ["A5A", "A5B", "A5C"]
    assert out["resolvable"] is True


def test_dangling_prerequisite_of_warmed_object():
    """A prerequisite of a warmed object that is not itself warmed (excluded) is dangling."""
    out = _drive([("A5A", 100000, "N5B"), ("N5B", 5, "-")])   # N5B is COLD -> not warmed
    assert _disp(out)["N5B"] == "COLD"
    assert out["dangling"] == [["A5A", "N5B"]]
    assert out["plan"] == ["A5A"]


def test_cycle_among_warmed_is_unresolvable():
    """A dependency cycle among warmed objects makes the plan unresolvable with an empty plan."""
    out = _drive([("A5A", 100000, "A5B"), ("A5B", 100000, "A5A")])
    assert out["resolvable"] is False and out["plan"] == []


def test_zzz_perturbation_on_generated_files():
    """Re-run reconcile on held-out generated descriptor files and deep-compare to the reference."""
    backup = open(DAT).read()
    seen = []
    try:
        for seed in [3, 19, 44, 70, 101, 222, 400, 777]:
            lock = R.generate(seed)
            open(DAT, "w").write(lock)
            got = _run("reconcile")
            assert got == _norm(R.stage2_reconcile(lock)), f"seed {seed}: reconcile mismatch"
            seen.append(json.dumps(got, sort_keys=True))
        assert len(set(seen)) > 1, "reconcile identical across inputs (hardcoded?)"
    finally:
        open(DAT, "w").write(backup)
