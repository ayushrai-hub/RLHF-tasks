"""Milestone 3 verifier: fold the order into a plan digest.

Re-runs the agent's /app/plan.pl digest on the bundled and held-out files, deep-comparing
/app/out/digest.json to the reference. Crafted cases pin the digest to the current revision's
djb2 accumulator (not FNV-1a) and the order_crc to a POSIX cksum of the newline-joined order
(cross-checked against /usr/bin/cksum), and confirm an unresolvable plan digests to nulls.
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


def _djb2(order):
    h = 5381
    for key in order:
        for ch in key.encode():
            h = ((h * 33) ^ ch) & 0xFFFFFFFF
    return h


def test_digest_shape():
    out = _run("digest")
    assert set(out) == {"plan_hash", "hit_sum", "order_crc"}


def test_digest_matches_reference_on_bundled():
    lock = open(DAT).read()
    assert _run("digest") == _norm(R.stage3_digest(lock))


def test_plan_hash_is_djb2_not_fnv():
    """The plan hash is djb2 (seed 5381, multiply by 33, XOR the byte). An FNV-1a hash would
    give a different value on the same order."""
    frames = [b"OBJ AA -", b"OBJ BB AA", b"HIT AA 3", b"HIT BB 4"]
    order = ["AA", "BB"]
    fnv = 2166136261
    for key in order:
        for ch in key.encode():
            fnv = ((fnv ^ ch) * 16777619) & 0xFFFFFFFF
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(_write(frames))
        out = _run("digest")
        assert out["plan_hash"] == _djb2(order), "plan_hash is not djb2 over the order"
        assert out["plan_hash"] != fnv, "plan_hash looks like FNV-1a (a superseded revision)"
    finally:
        open(DAT, "w").write(backup)


def test_order_crc_is_posix_cksum_of_newline_joined_order():
    """order_crc equals /usr/bin/cksum of the order written one key per line."""
    frames = [b"OBJ AA -", b"OBJ BB AA", b"OBJ CC BB", b"HIT AA 1", b"HIT BB 1", b"HIT CC 1"]
    order = ["AA", "BB", "CC"]
    blob = ("".join(k + "\n" for k in order)).encode()
    real = int(subprocess.run(["cksum"], input=blob, capture_output=True).stdout.split()[0])
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(_write(frames))
        out = _run("digest")
        assert out["order_crc"] == real, "order_crc must be POSIX cksum of the newline-joined order"
        assert out["hit_sum"] == 3
    finally:
        open(DAT, "w").write(backup)


def test_unresolvable_digests_to_nulls():
    frames = [b"OBJ AA BB", b"OBJ BB AA", b"HIT AA 1", b"HIT BB 1"]
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(_write(frames))
        out = _run("digest")
        assert out == {"plan_hash": None, "hit_sum": None, "order_crc": None}
    finally:
        open(DAT, "w").write(backup)


def test_zzz_perturbation_on_generated_files():
    backup = open(DAT).read()
    seen = []
    try:
        for seed in [8, 21, 55, 90, 130, 300, 512, 888]:
            lock = R.generate(seed)
            open(DAT, "w").write(lock)
            got = _run("digest")
            assert got == _norm(R.stage3_digest(lock)), f"seed {seed}: digest mismatch"
            seen.append(json.dumps(got, sort_keys=True))
        assert len(set(seen)) > 1, "digest identical across inputs (hardcoded?)"
    finally:
        open(DAT, "w").write(backup)
