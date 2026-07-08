"""Milestone 2 verifier: reconcile and order the warm-up plan.

Re-runs the agent's /app/plan.pl order on the bundled and held-out files, deep-comparing
/app/out/order.json to the reference. Crafted cases catch the revision traps: an OUTER join
(R2) instead of the inner join, and a weight- or sequence-based tie-break (R3/R4) instead of
the C-locale key tie-break.
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


def _write(frames):
    return "".join(_frame(i + 1, r) + "\n" for i, r in enumerate(frames))


def test_order_shape():
    out = _run("order")
    assert set(out) == {"resolvable", "order", "joined", "dangling"}
    assert isinstance(out["resolvable"], bool)


def test_order_matches_reference_on_bundled():
    lock = open(DAT).read()
    assert _run("order") == _norm(R.stage2_order(lock))


def test_join_is_inner_not_outer():
    """An object with an OBJ but no HIT is NOT in the plan (inner join); an R2 outer join would
    include it with a phantom weight."""
    frames = [b"OBJ AA -", b"OBJ BB -", b"HIT AA 5"]     # BB has no HIT
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(_write(frames))
        out = _run("order")
        assert out["joined"] == ["AA"], "BB has no HIT and must be excluded (inner join)"
        assert out["order"] == ["AA"]
    finally:
        open(DAT, "w").write(backup)


def test_tie_break_is_c_locale_not_weight_or_sequence():
    """Two independent ready objects must be ordered by C-locale key ascending, regardless of
    their hit weights or frame order. Here AA is lighter than BB and appears later in the file,
    so a weight- or sequence-based tie-break would emit BB first; C-locale emits AA first."""
    frames = [b"HIT BB 999", b"OBJ BB -", b"HIT AA 1", b"OBJ AA -"]
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(_write(frames))
        out = _run("order")
        assert out["order"] == ["AA", "BB"], f"expected C-locale order, got {out['order']}"
    finally:
        open(DAT, "w").write(backup)


def test_topological_prerequisites_precede():
    """Prerequisites are warmed before dependents; ties among ready objects still C-locale."""
    frames = [b"OBJ CC AA,BB", b"OBJ AA -", b"OBJ BB -",
              b"HIT AA 1", b"HIT BB 1", b"HIT CC 1"]
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(_write(frames))
        out = _run("order")
        assert out["order"] == ["AA", "BB", "CC"]
        assert out["resolvable"] is True
    finally:
        open(DAT, "w").write(backup)


def test_dangling_prerequisites_reported():
    """A prerequisite of a joined object that is not itself joined is dangling, not added."""
    frames = [b"OBJ AA MM", b"HIT AA 3"]                  # MM has no OBJ/HIT
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(_write(frames))
        out = _run("order")
        assert out["joined"] == ["AA"]
        assert [["AA", "MM"]] == out["dangling"]
        assert out["order"] == ["AA"]
    finally:
        open(DAT, "w").write(backup)


def test_cycle_is_unresolvable():
    """A dependency cycle among joined objects makes the plan unresolvable with an empty order."""
    frames = [b"OBJ AA BB", b"OBJ BB AA", b"HIT AA 1", b"HIT BB 1"]
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(_write(frames))
        out = _run("order")
        assert out["resolvable"] is False
        assert out["order"] == []
        assert out["joined"] == ["AA", "BB"]
    finally:
        open(DAT, "w").write(backup)


def test_zzz_perturbation_on_generated_files():
    backup = open(DAT).read()
    seen = []
    try:
        for seed in [3, 19, 44, 70, 101, 222, 400, 777]:
            lock = R.generate(seed)
            open(DAT, "w").write(lock)
            got = _run("order")
            assert got == _norm(R.stage2_order(lock)), f"seed {seed}: order mismatch"
            seen.append(json.dumps(got, sort_keys=True))
        assert len(set(seen)) > 1, "order identical across inputs (hardcoded?)"
    finally:
        open(DAT, "w").write(backup)
