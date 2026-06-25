"""Verifier harness for h7_trace.json observation matrix."""

import json
import subprocess
from pathlib import Path

import pytest

ENV = Path("/app/environment")
OUT = Path("/app/output/h7_trace.json")
STAGE_A = ENV / "fixtures" / "stage_a.dat"
STAGE_B = ENV / "fixtures" / "stage_b.dat"
ROUND_SEQ = Path("/app/work/round.seq")

EMIT_ORDER = [
    ("w0_short", "direct"),
    ("w0_short", "svc"),
    ("w0_long", "direct"),
    ("w0_long", "svc"),
]

ROUND_CHAIN = list(EMIT_ORDER)

def _fnv_params() -> tuple[int, int]:
    text = (ENV / "docs" / "h3_seal.md").read_text(encoding="utf-8")
    import re

    basis_m = re.search(r"basis `(\d+)`", text)
    prime_m = re.search(r"prime `(\d+)`", text)
    assert basis_m and prime_m, "FNV constants documented in h3_seal.md"
    return int(basis_m.group(1)), int(prime_m.group(1))


def _sha256_hex(payload: bytes) -> str:
    proc = subprocess.run(["sha256sum"], input=payload, capture_output=True, check=True)
    return proc.stdout.split()[0].decode()


def _file_digest(path: Path) -> str:
    return _sha256_hex(path.read_bytes())


def _fnv1a64(data: bytes) -> int:
    basis, prime = _fnv_params()
    h = basis
    for b in data:
        h ^= b
        h = (h * prime) % (1 << 64)
    return h


def _hex16(v: int) -> str:
    return f"{v:016x}"


def _matrix_seal(rows: list[dict]) -> str:
    by_key = {(r["profile"], r["principal"]): r for r in rows}
    lines: list[str] = []
    for profile, principal in EMIT_ORDER:
        row = by_key[(profile, principal)]
        lines.append(
            f"{row['profile']}|{row['principal']}|{row['reach_digest']}|{row['chain_seq']}\n"
        )
    return _hex16(_fnv1a64("".join(lines).encode()))


def _marks_threshold(marks: str) -> int:
    if not marks:
        return 5
    last = marks[-1]
    if last.isdigit() and int(last) % 2 == 1:
        return 4
    return 5


def _token_count(token_line: str) -> int:
    return len([part for part in token_line.split() if part])


def _expected_pick(profile: str) -> int:
    token = _env_value(profile, "TOKEN")
    marks = _env_value(profile, "MARKS")
    threshold = _marks_threshold(marks)
    return 1 if _token_count(token) >= threshold else 0


def _env_value(profile: str, key: str) -> str:
    text = (ENV / "fixtures" / f"{profile}.env").read_text(encoding="utf-8")
    prefix = f"{key}="
    for line in text.splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1]
    raise AssertionError(f"missing {key} in {profile}.env")


def _rule_count(profile: str) -> int:
    marks = _env_value(profile, "MARKS")
    non_space = len([c for c in marks if not c.isspace()])
    return non_space + _token_count(_env_value(profile, "TOKEN"))


def _expected_carry_prefix() -> bytes:
    pick = _expected_pick("w0_short")
    base = _expected_reach("w0_short", pick, use_carry=False)
    return base[:8].encode("utf-8")


def _expected_reach(profile: str, pick: int, use_carry: bool = False) -> str:
    envelope = _env_value(profile, "ENVELOPE").encode("utf-8")
    stage = STAGE_B.read_bytes() if pick == 1 else STAGE_A.read_bytes()
    extra = _expected_carry_prefix() if profile == "w0_long" and use_carry else b""
    return _sha256_hex(envelope + stage + extra)[:16]


def _expected_self_check(reach: str, handoff: str, rules: int) -> str:
    payload = f"{reach}{handoff}{rules}".encode("utf-8")
    return _sha256_hex(payload)[:16]


def _snap_mark(seed_path: Path, admission: str) -> str:
    seed = seed_path.read_text(encoding="utf-8").strip()
    return _sha256_hex((seed + admission).encode("utf-8"))[:8]


def _snap_b_admission(principal: str, admission: str, reach: str, profile: str, pick: int) -> str:
    if reach == _expected_reach(profile, pick):
        return admission
    if principal == "svc":
        return "hold"
    return "open"


def _expected_admit(principal: str) -> str:
    return "hold" if principal == "svc" else "open"


def _build_c() -> None:
    result = subprocess.run(
        ["make", "-C", "/app/environment", "all"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"C build failed:\n{result.stderr}"


def _build_stamp() -> None:
    proc = subprocess.run(
        ["/usr/local/go/bin/go", "build", "-o", "/app/bin/h7stamp", "./cmd/h7stamp"],
        cwd="/app/environment",
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr


def _build_all() -> None:
    _build_c()
    _build_stamp()


@pytest.fixture(scope="session", autouse=True)
def _session_build() -> None:
    _build_all()


def _reset_output() -> None:
    if OUT.exists():
        OUT.unlink()


def _reset_work() -> None:
    work = Path("/app/work")
    work.mkdir(parents=True, exist_ok=True)
    for child in work.iterdir():
        if child.is_file():
            child.unlink()


def _round(profile: str, principal: str) -> None:
    subprocess.run(
        [
            "/app/environment/tools/k7_round",
            "--profile",
            profile,
            "--principal",
            principal,
        ],
        check=True,
    )


def _emit() -> dict:
    subprocess.run(["/app/environment/tools/m4_emit"], check=True)
    assert OUT.exists(), "m4_emit must recreate h7_trace.json"
    return json.loads(OUT.read_text(encoding="utf-8"))


def _full_chain() -> dict:
    _reset_output()
    subprocess.run(["/app/environment/d0/h7_drv", "clear"], check=True)
    for profile, principal in ROUND_CHAIN:
        _round(profile, principal)
    return _emit()


def _row(doc: dict, profile: str, principal: str) -> dict:
    for row in doc["rows"]:
        if row["profile"] == profile and row["principal"] == principal:
            return row
    raise AssertionError(f"missing row profile={profile} principal={principal}")


def test_z0_a0_schema() -> None:
    """Four rows appear in contract emit order with chain_seq and h7-v1 summary."""
    trace_doc = _full_chain()
    assert set(trace_doc) == {"rows", "summary"}
    assert trace_doc["summary"]["row_count"] == 4
    assert trace_doc["summary"]["trace_stamp"] == "h7-v1"
    assert len(trace_doc["summary"]["matrix_seal"]) == 16
    int(trace_doc["summary"]["matrix_seal"], 16)
    assert len(trace_doc["rows"]) == 4
    required = {
        "profile",
        "principal",
        "fixture_tag",
        "stage_digest_hex",
        "reach_digest",
        "self_check_field",
        "admit_code",
        "snap_a_mark",
        "snap_b_mark",
        "handoff_label",
        "layer_pick",
        "rule_count",
        "chain_seq",
    }
    for idx, (profile, principal) in enumerate(EMIT_ORDER):
        row = trace_doc["rows"][idx]
        assert row["profile"] == profile
        assert row["principal"] == principal
        assert required <= set(row)
        assert row["fixture_tag"] == profile
        assert len(row["stage_digest_hex"]) == 64
        assert len(row["reach_digest"]) == 16
        assert len(row["self_check_field"]) == 16
        assert len(row["snap_a_mark"]) == 8
        assert len(row["snap_b_mark"]) == 8
        int(row["stage_digest_hex"], 16)
        assert isinstance(row["chain_seq"], int)
        assert row["chain_seq"] == idx


def test_z1_a1_digest() -> None:
    """stage_digest_hex and reach_digest match staged selection and long-profile carry."""
    trace_doc = _full_chain()
    for profile, principal in EMIT_ORDER:
        row = _row(trace_doc, profile, principal)
        pick = _expected_pick(profile)
        expected_stage = STAGE_B if pick == 1 else STAGE_A
        use_carry = profile == "w0_long"
        assert row["layer_pick"] == pick
        assert row["stage_digest_hex"] == _file_digest(expected_stage)
        assert row["reach_digest"] == _expected_reach(profile, pick, use_carry=use_carry)


def test_z2_a2_align() -> None:
    """self_check_field matches rolling digest for every profile and principal."""
    trace_doc = _full_chain()
    for profile, principal in EMIT_ORDER:
        row = _row(trace_doc, profile, principal)
        pick = _expected_pick(profile)
        rules = _rule_count(profile)
        handoff = "inherited"
        want = _expected_self_check(row["reach_digest"], handoff, rules)
        assert row["self_check_field"] == want
        assert row["reach_digest"] == _expected_reach(
            profile, pick, use_carry=profile == "w0_long"
        )


def test_z3_a3_persist() -> None:
    """Trace store alone rebuilds the matrix after scratch state files are removed."""
    trace_doc = _full_chain()
    carry_path = Path("/app/work/profile_carry.txt")
    assert carry_path.is_file(), "carry file must exist after w0_short/svc round"
    assert carry_path.read_text().strip() == _expected_carry_prefix().decode()
    for scratch in (
        Path("/app/work/row_state.env"),
        Path("/app/work/round.seq"),
        carry_path,
    ):
        if scratch.exists():
            scratch.unlink()
    replay = _emit()
    assert replay == trace_doc
    first_bytes = OUT.read_bytes()
    third = _emit()
    assert third == trace_doc
    assert OUT.read_bytes() == first_bytes


def test_z4_a4_columns() -> None:
    """snap_a and snap_b marks follow seed rules for every profile and principal."""
    trace_doc = _full_chain()
    for profile, principal in EMIT_ORDER:
        row = _row(trace_doc, profile, principal)
        pick = _expected_pick(profile)
        admit = row["admit_code"]
        assert row["snap_a_mark"] == _snap_mark(ENV / "fixtures" / "snap_a_seed.txt", admit)
        b_admit = _snap_b_admission(principal, admit, row["reach_digest"], profile, pick)
        assert row["snap_b_mark"] == _snap_mark(ENV / "fixtures" / "snap_b_seed.txt", b_admit)
        if principal == "svc":
            assert b_admit == admit
        assert row["reach_digest"] == _expected_reach(
            profile, pick, use_carry=profile == "w0_long"
        )
        assert row["admit_code"] == _expected_admit(principal)


def test_z5_a5_rule_coupling() -> None:
    """rule_count and self_check_field stay coupled when install tally is one short."""
    trace_doc = _full_chain()
    for profile, principal in EMIT_ORDER:
        row = _row(trace_doc, profile, principal)
        rules = _rule_count(profile)
        assert row["rule_count"] == rules
        handoff = row["handoff_label"]
        want_self = _expected_self_check(row["reach_digest"], handoff, rules)
        assert row["self_check_field"] == want_self
        broken_rules = rules - 1
        assert row["self_check_field"] != _expected_self_check(
            row["reach_digest"], handoff, broken_rules
        )
    first_bytes = OUT.read_bytes()
    second = _emit()
    assert second == trace_doc
    assert OUT.read_bytes() == first_bytes


def test_z6_a6_seal() -> None:
    """summary.matrix_seal matches emit-order FNV seal over reach_digest and chain_seq lines."""
    trace_doc = _full_chain()
    want = _matrix_seal(trace_doc["rows"])
    assert trace_doc["summary"]["matrix_seal"] == want


def test_z7_a7_ledger() -> None:
    """h7_drv clear resets round.seq so chain_seq restarts at zero on a fresh chain."""
    _reset_output()
    _reset_work()
    ROUND_SEQ.write_text("9\n")
    subprocess.run(["/app/environment/d0/h7_drv", "clear"], check=True)
    assert not ROUND_SEQ.exists() or ROUND_SEQ.read_text().strip() in {"", "0"}
    for profile, principal in ROUND_CHAIN:
        _round(profile, principal)
    trace_doc = _emit()
    for idx, (profile, principal) in enumerate(EMIT_ORDER):
        assert _row(trace_doc, profile, principal)["chain_seq"] == idx


def test_z8_a8_replay() -> None:
    """Fresh chains match only when carry and ledger reset together with the trace store."""

    def one_run() -> dict:
        _reset_output()
        subprocess.run(["/app/environment/d0/h7_drv", "clear"], check=True)
        for profile, principal in ROUND_CHAIN:
            _round(profile, principal)
        return _emit()

    first = one_run()
    second = one_run()
    assert first["summary"]["matrix_seal"] == second["summary"]["matrix_seal"]
    for profile, principal in EMIT_ORDER:
        a = _row(first, profile, principal)
        b = _row(second, profile, principal)
        assert a["reach_digest"] == b["reach_digest"]
        assert a["stage_digest_hex"] == b["stage_digest_hex"]

    long_pick = _expected_pick("w0_long")
    long_row = _row(first, "w0_long", "direct")
    assert long_row["reach_digest"] != _expected_reach("w0_long", long_pick, use_carry=False)
    assert long_row["reach_digest"] == _expected_reach("w0_long", long_pick, use_carry=True)


def test_z9_a9_ledger_capture() -> None:
    """chain_seq records the ledger value before advance, not the post-round counter."""
    _reset_output()
    _reset_work()
    subprocess.run(["/app/environment/d0/h7_drv", "clear"], check=True)
    for idx, (profile, principal) in enumerate(ROUND_CHAIN):
        _round(profile, principal)
        if ROUND_SEQ.exists():
            ledger_val = int(ROUND_SEQ.read_text().strip())
            assert ledger_val == idx + 1
    trace_doc = _emit()
    for idx, (profile, principal) in enumerate(EMIT_ORDER):
        row = _row(trace_doc, profile, principal)
        assert row["chain_seq"] == idx
    assert int(ROUND_SEQ.read_text().strip()) == len(ROUND_CHAIN)
