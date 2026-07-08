"""Milestone 1 verifier: decode warm-cache frames.

Re-runs the agent's /app/plan.pl on the bundled descriptor file and on held-out generated
files, deep-comparing /app/out/decode.json to an independent reference. Grading is tied to the
agent's source (the program is re-run), and the held-out inputs defeat a hardcoded report.
Crafted frames catch the two revision traps: checksumming the base64 transport instead of the
decoded content (R4), and accepting base64url instead of canonical base64.
"""
import base64
import json
import os
import re
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


def test_plan_pl_exists():
    assert os.path.exists(SRC), "/app/plan.pl is missing"


def test_decode_shape():
    out = _run("decode")
    assert set(out) == {"objs", "hits", "invalid"}
    for k in ("objs", "hits", "invalid"):
        assert isinstance(out[k], list)


def test_decode_matches_reference_on_bundled():
    lock = open(DAT).read()
    assert _run("decode") == _norm(R.stage1_decode(lock))


def test_checksum_is_over_decoded_bytes_not_base64():
    """A frame whose CRC is cksum(decoded bytes) must be ACCEPTED; an R4-style reader that
    checksums the base64 transport would wrongly reject it."""
    rec = b"OBJ AB CD"
    crc = R.cksum_crc(rec)
    assert R.cksum_crc(base64.b64encode(rec)) != crc  # transport CRC differs from content CRC
    lock = _frame(1, rec) + "\n" + _frame(2, b"HIT AB 5") + "\n"
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(lock)
        out = _run("decode")
        assert ["AB", ["CD"]] in out["objs"], "valid current frame was rejected"
        assert out["invalid"] == []
    finally:
        open(DAT, "w").write(backup)


def test_base64url_payload_is_rejected():
    """base64url (- and _ instead of + and /) is NOT canonical base64 and must be BAD_B64."""
    raw = bytes([251, 255, 191])                       # encodes with + and / in standard base64
    std = base64.b64encode(raw).decode()
    url = base64.urlsafe_b64encode(raw).decode()
    assert url != std and ("-" in url or "_" in url)
    lock = "1 %s %d\n" % (url, R.cksum_crc(raw))
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(lock)
        out = _run("decode")
        assert [1, "BAD_B64"] in out["invalid"], "base64url payload was not rejected as BAD_B64"
    finally:
        open(DAT, "w").write(backup)


def test_bad_frames_are_coded():
    """Malformed frames are reported with the documented codes, not dropped."""
    good = b"HIT AB 5"
    lock = "".join([
        "1 not@base64 999\n",                                  # BAD_B64
        "2 %s %d\n" % (base64.b64encode(good).decode(), R.cksum_crc(good) ^ 7),  # BAD_CRC
        "3 %s\n" % base64.b64encode(b"OBJ QQ -").decode(),     # BAD_FRAME (2 fields)
        _frame(4, b"ZZZ X 1") + "\n",                          # BAD_KIND
        _frame(5, good) + "\n",                                # valid
    ])
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(lock)
        out = _run("decode")
        inv = {tuple(e) for e in out["invalid"]}
        assert (1, "BAD_B64") in inv
        assert (2, "BAD_CRC") in inv
        assert (3, "BAD_FRAME") in inv
        assert (4, "BAD_KIND") in inv
        assert ["AB", 5] in out["hits"]
    finally:
        open(DAT, "w").write(backup)


def test_duplicate_records_are_coded():
    """A second OBJ (or HIT) for a key already seen is DUP; first occurrence wins."""
    lock = _frame(1, b"OBJ QQ -") + "\n" + _frame(2, b"OBJ QQ RR") + "\n"
    backup = open(DAT).read()
    try:
        open(DAT, "w").write(lock)
        out = _run("decode")
        assert ["QQ", []] in out["objs"], "first OBJ should win"
        assert [2, "DUP"] in out["invalid"]
    finally:
        open(DAT, "w").write(backup)


def test_zzz_perturbation_on_generated_files():
    """Re-run decode on held-out generated descriptor files and deep-compare."""
    backup = open(DAT).read()
    seen = []
    try:
        for seed in [5, 17, 33, 61, 88, 140, 257, 909]:
            lock = R.generate(seed)
            open(DAT, "w").write(lock)
            got = _run("decode")
            assert got == _norm(R.stage1_decode(lock)), f"seed {seed}: decode mismatch"
            seen.append(json.dumps(got, sort_keys=True))
        assert len(set(seen)) > 1, "decode identical across inputs (hardcoded?)"
    finally:
        open(DAT, "w").write(backup)


def test_tool_is_perl_and_does_not_shell_out():
    """/app/plan.pl reads the descriptor and does not delegate to a general interpreter (POSIX
    coreutils like cksum/base64/sort/join/cut/mkdir are allowed)."""
    assert os.path.exists(SRC)
    src = re.sub(r"#[^\n]*", " ", open(SRC).read())
    assert "warmcache.dat" in src, "plan.pl must read /app/warmcache.dat"
    for bad in (r"\bpython\d?\b", r"\bruby\b", r"\blua\d?\b", r"\bnode\b",
                r"\bg?awk\b", r"\bphp\b", r"\btclsh\b"):
        assert not re.search(bad, src), f"must not delegate to {bad!r}"
