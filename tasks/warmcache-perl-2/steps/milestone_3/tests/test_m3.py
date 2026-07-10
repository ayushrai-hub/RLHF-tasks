"""Milestone 3 verifier: roll up the warmed objects by zone.

Re-runs the agent's /app/plan.pl rollup on the bundled and held-out files, deep-comparing
/app/out/rollup.json to the reference. Crafted cases pin the retention policy whose values the
chronicle settles through its amendment chain: the retain minimum is 2 (an older value 3 is
superseded) and W is the only priority zone (V was merged into W). The digest is the POSIX cksum
of the canonical retained-zone block, cross-checked against /usr/bin/cksum.
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
    lines, s = [], 1
    for key, _w, pre in objs:
        lines.append(_frame(s, ("OBJ %s %s" % (key, pre)).encode()))
        s += 1
    for key, w, _pre in objs:
        lines.append(_frame(s, ("HIT %s %d" % (key, w)).encode()))
        s += 1
    return "".join(x + "\n" for x in lines)


def _drive(objs):
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(_write(objs))
        out = _run("rollup")
        assert _norm(out) == _norm(R.stage3_rollup(open(DAT).read()))
        return out
    finally:
        open(DAT, "w").write(backup)


def test_rollup_shape():
    """rollup.json is a JSON object with zones, overflow, total and digest."""
    out = _run("rollup")
    assert set(out) == {"zones", "overflow", "total", "digest"}


def test_rollup_matches_reference_on_bundled():
    """The rollup of the bundled descriptor file equals the independent reference exactly."""
    lock = open(DAT).read()
    assert _run("rollup") == _norm(R.stage3_rollup(lock))


def test_retention_count_priority_and_overflow():
    """A zone with two warmed objects is retained; a single-object non-priority zone overflows; a
    single-object priority zone (W) is retained. Totals and overflow sums are exact."""
    out = _drive([("A5A", 100000, "-"), ("A6B", 100000, "-"),   # zone A: 2 -> retained
                  ("B5C", 100000, "-"),                          # zone B: 1 -> overflow
                  ("W5D", 100000, "-")])                         # zone W: 1 -> retained (priority)
    assert out["zones"] == [["A", 2, 200000], ["W", 1, 100000]]
    assert out["overflow"] == {"count": 1, "weight": 100000}
    assert out["total"] == {"count": 4, "weight": 400000}


def test_retain_min_is_two_not_three():
    """The retain minimum is 2: a zone with exactly two warmed objects is retained (a solver using
    the superseded minimum of 3 would overflow it)."""
    out = _drive([("C5A", 100000, "-"), ("C6B", 100000, "-")])
    assert out["zones"] == [["C", 2, 200000]]
    assert out["overflow"] == {"count": 0, "weight": 0}


def test_priority_zone_v_is_superseded():
    """Priority zones are just W; zone V (merged into W) is NOT priority, so a single V object
    overflows rather than being retained."""
    out = _drive([("V5A", 100000, "-")])
    assert out["zones"] == []
    assert out["overflow"] == {"count": 1, "weight": 100000}


def test_digest_is_posix_cksum_of_zone_block():
    """digest equals /usr/bin/cksum of the canonical retained-zone block (zone count weight lines)."""
    out = _drive([("A5A", 100000, "-"), ("A6B", 100000, "-"), ("W5D", 100000, "-")])
    block = b"A 2 200000\nW 1 100000\n"
    real = int(subprocess.run(["cksum"], input=block, capture_output=True).stdout.split()[0])
    assert out["digest"] == real


def test_no_retained_zone_digests_empty_string():
    """With no retained zone the digest is the cksum of the empty string."""
    out = _drive([("B5A", 100000, "-")])                        # zone B single -> overflow, none retained
    empty = int(subprocess.run(["cksum"], input=b"", capture_output=True).stdout.split()[0])
    assert out["zones"] == [] and out["digest"] == empty


def test_unresolvable_rolls_up_to_nulls():
    """When the warmed objects contain a cycle the rollup is empty zones and null fields."""
    out = _drive([("A5A", 100000, "A5B"), ("A5B", 100000, "A5A")])
    assert out == {"zones": [], "overflow": None, "total": None, "digest": None}


def test_zzz_perturbation_on_generated_files():
    """Re-run rollup on held-out generated descriptor files and deep-compare to the reference."""
    backup = open(DAT).read()
    seen = []
    try:
        for seed in [8, 21, 55, 90, 130, 300, 512, 888]:
            lock = R.generate(seed)
            open(DAT, "w").write(lock)
            got = _run("rollup")
            assert got == _norm(R.stage3_rollup(lock)), f"seed {seed}: rollup mismatch"
            seen.append(json.dumps(got, sort_keys=True))
        assert len(set(seen)) > 1, "rollup identical across inputs (hardcoded?)"
    finally:
        open(DAT, "w").write(backup)
