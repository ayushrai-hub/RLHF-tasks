"""Verifier for cap_audit.json audit bundle."""

import json
import shutil
import subprocess

import pytest
from pathlib import Path

ENV = Path("/app/environment")
OUT = Path("/app/output/cap_audit.json")
WORK = Path("/app/work")

AUTH_TABLE = ENV / "q2_auth" / "auth_table"
BRIDGE_FIXTURE = ENV / "fixtures/q8/r3_bridge.dat"


def _auth_tag(mark: str) -> int:
    for line in AUTH_TABLE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        name, tag = line.split("\t", 1)
        if name == mark:
            return int(tag)
    raise AssertionError(f"missing auth_table row for mark={mark}")


def _bridge_lab_effective() -> str:
    prefix = "bridge_effective"
    for line in BRIDGE_FIXTURE.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            return line[len(prefix) + 1 :]
    raise AssertionError("missing bridge_effective in r3_bridge.dat")


def _fixture_text(path: Path, key: str) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1]
    raise AssertionError(f"missing {key} in {path}")


def _actor_hex(actor: str, key: str) -> int:
    return int(_fixture_text(ENV / "actors" / f"{actor}.env", key), 0)


CLASS_INTERACTIVE = _auth_tag("wrap_r0")
BASE_EFFECTIVE = _fixture_text(ENV / "fixtures/q8/base.dat", "effective")
BASE_BOUND = _fixture_text(ENV / "fixtures/q8/base.dat", "bound")
BTWO_AMBIENT_MASK = _actor_hex("b_two", "AMBIENT_MASK")
POST_REQUIRED = int(_fixture_text(ENV / "fixtures/q8/post_step.dat", "required"), 0)
GAP_NESTED = _fixture_text(ENV / "fixtures/q8/post_step.dat", "gap_code")
GAP_CLEAR = "G0"


def _open_stamp() -> int:
    for line in (ENV / "fixtures/q8/post_step.dat").read_text(encoding="utf-8").splitlines():
        if line.startswith("open_stamp="):
            return int(line.split("=", 1)[1], 0)
    raise AssertionError("missing open_stamp in post_step.dat")


def _sha256_hex(payload: bytes) -> str:
    proc = subprocess.run(["sha256sum"], input=payload, capture_output=True, check=True)
    return proc.stdout.split()[0].decode()


def _effective_set_hash(round_id: str, actor: str, mark: str, class_tag: int, cap_effective: str, cap_bound: str) -> str:
    body = json.dumps(
        {
            "actor": actor,
            "cap_bound": cap_bound,
            "cap_effective": cap_effective,
            "class_tag": class_tag,
            "mark": mark,
            "round": round_id,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    return _sha256_hex(body.encode("utf-8"))


def _bound_set_hash(cap_bound: str) -> str:
    return _sha256_hex(cap_bound.encode("utf-8"))


def _ambient_merged_effective(base_hex: str, ambient_mask: int) -> str:
    base = int(base_hex, 16)
    return f"0x{(base | ambient_mask) & 0xFF:02x}"


def _bundle_digest(rows: list[dict]) -> str:
    lines = sorted(
        f"{r['round']},{r['actor']},{r['mark']},{r['effective_set_hash']},{r['bound_set_hash']},{r['seq_code']}"
        for r in rows
    )
    body = ("\n".join(lines) + "\n").encode("utf-8")
    return _sha256_hex(body)


def _reset_workspace() -> None:
    if OUT.exists():
        OUT.unlink()
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True, exist_ok=True)


def _build() -> None:
    subprocess.run(["make", "-C", "/app/environment", "all"], check=True)


def _round(round_id: str, actor: str, mark: str, launch: str = "") -> None:
    if launch:
        subprocess.run(
            [
                "/app/environment/tools/k9_round",
                "--round",
                round_id,
                "--actor",
                actor,
                "--mark",
                mark,
                "--launch",
                launch,
            ],
            check=True,
        )
        return
    subprocess.run(
        [
            "/app/environment/tools/k9_round",
            "--round",
            round_id,
            "--actor",
            actor,
            "--mark",
            mark,
        ],
        check=True,
    )


def _publish() -> dict:
    subprocess.run(
        ["/app/environment/tools/m2_publish", "--out", "/app/output/cap_audit.json"],
        check=True,
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


def _row(doc: dict, round_id: str, actor: str, mark: str) -> dict:
    for row in doc["rows"]:
        if row["round"] == round_id and row["actor"] == actor and row["mark"] == mark:
            return row
    raise AssertionError(f"missing row round={round_id} actor={actor} mark={mark}")


def _full_chain() -> dict:
    _reset_workspace()
    _build()
    _round("r0", "a_one", "wrap_r0", "sync")
    _round("r0", "a_one", "direct_bypass", "direct")
    _round("r1", "a_one", "wrapped_p1", "sync")
    _round("r1", "a_one", "direct_bypass", "direct")
    _round("r2", "b_two", "direct_r1", "direct")
    _round("r3", "c_three", "wrapped_r2", "sync")
    _round("r3", "c_three", "direct_r2", "direct")
    return _publish()


def _assert_canonical_rows(doc: dict) -> None:
    keys = [(r["round"], r["actor"], r["mark"]) for r in doc["rows"]]
    assert keys == sorted(keys), "rows must be sorted round, actor, mark"
    assert doc["bundle_digest"] == _bundle_digest(doc["rows"])


def _nnp_routed_bound_hex() -> str:
    eff = int(BASE_EFFECTIVE, 16)
    bnd = int(BASE_BOUND, 16)
    routed = (eff & 0xF0) | (bnd & 0x0F)
    return f"0x{routed:02x}"


def test_c00_nnp_bound_route() -> None:
    """NoNewPrivs unit fixture routes published bound_set_hash through base.dat mask merge."""
    _reset_workspace()
    _build()
    _round("r0", "a_one", "wrap_r0", "sync")
    doc = _publish()
    row = _row(doc, "r0", "a_one", "wrap_r0")
    expected_bound = _nnp_routed_bound_hex()
    assert row["bound_set_hash"] == _bound_set_hash(expected_bound)
    assert row["bound_set_hash"] != _bound_set_hash(f"0x{int(BASE_EFFECTIVE, 16) & 0x7F:02x}")


def test_c01_auth_table_fidelity() -> None:
    """Every published mark uses the tabulated class_tag from auth_table without lane overrides."""
    doc = _full_chain()
    marks = [
        ("r0", "a_one", "wrap_r0"),
        ("r0", "a_one", "direct_bypass"),
        ("r1", "a_one", "wrapped_p1"),
        ("r1", "a_one", "direct_bypass"),
        ("r2", "b_two", "direct_r1"),
        ("r3", "c_three", "wrapped_r2"),
        ("r3", "c_three", "direct_r2"),
    ]
    for round_id, actor, mark in marks:
        row = _row(doc, round_id, actor, mark)
        assert row["class_tag"] == _auth_tag(mark)
        assert row["class_tag"] != 5, "wrapped marks must inherit auth_table tags, not lane overrides"


def test_c02_gap_trace() -> None:
    """Wrapped round-one mark clears gap after post-step subset is present; direct stays aligned with base."""
    doc = _full_chain()
    wrapped = _row(doc, "r1", "a_one", "wrapped_p1")
    direct = _row(doc, "r1", "a_one", "direct_bypass")
    assert wrapped["gap_code"] == GAP_CLEAR
    assert direct["gap_code"] == GAP_CLEAR
    expected_direct = _effective_set_hash("r1", "a_one", "direct_bypass", CLASS_INTERACTIVE, BASE_EFFECTIVE, BASE_BOUND)
    assert direct["effective_set_hash"] == expected_direct


def test_c03_bound_delta() -> None:
    """Sync and direct launch paths converge on the base bound hash at round one."""
    doc = _full_chain()
    wrapped = _row(doc, "r1", "a_one", "wrapped_p1")
    direct = _row(doc, "r1", "a_one", "direct_bypass")
    assert wrapped["bound_set_hash"] == _bound_set_hash(BASE_BOUND)
    assert direct["bound_set_hash"] == _bound_set_hash(BASE_BOUND)
    assert wrapped["bound_set_hash"] == direct["bound_set_hash"]


def test_c04_stamp_subset() -> None:
    """Wrapped round-one rows carry open stamp and include post-step subset in effective hash."""
    doc = _full_chain()
    wrapped = _row(doc, "r1", "a_one", "wrapped_p1")
    assert wrapped["stamp_code"] == _open_stamp()
    eff_with_subset = f"0x{(int(BASE_EFFECTIVE, 16) | POST_REQUIRED) & 0xFF:02x}"
    expected = _effective_set_hash(
        "r1", "a_one", "wrapped_p1", CLASS_INTERACTIVE, eff_with_subset, BASE_BOUND
    )
    assert wrapped["effective_set_hash"] == expected


def test_c05_journal_merge_required() -> None:
    """After double replay of the same mark, merge_tail must keep the latest journal seq on publish."""
    _reset_workspace()
    _build()
    _round("r0", "a_one", "wrap_r0", "sync")
    _round("r0", "a_one", "wrap_r0", "sync")
    doc = _publish()
    row = _row(doc, "r0", "a_one", "wrap_r0")
    assert row["seq_code"] >= 2, "stale journal merge leaves first-generation seq on publish"


def test_c06_warm_replay_stable() -> None:
    """Second publish without source edits matches first bundle_digest bytes."""
    _full_chain()
    first = OUT.read_bytes()
    _publish()
    second = OUT.read_bytes()
    assert first == second
    doc = json.loads(first.decode())
    _assert_canonical_rows(doc)


def test_c07_r3_bridge_inherit() -> None:
    """Round-three bridge actor inherits reconciled round-two ops direct effective mask."""
    doc = _full_chain()
    ops_effective = _ambient_merged_effective(BASE_EFFECTIVE, BTWO_AMBIENT_MASK)
    b_row = _row(doc, "r2", "b_two", "direct_r1")
    b_expected = _effective_set_hash(
        "r2", "b_two", "direct_r1", CLASS_INTERACTIVE, ops_effective, BASE_BOUND
    )
    assert b_row["effective_set_hash"] == b_expected
    bridge = _row(doc, "r3", "c_three", "wrapped_r2")
    expected_wrapped = _effective_set_hash(
        "r3", "c_three", "wrapped_r2", CLASS_INTERACTIVE, ops_effective, BASE_BOUND
    )
    assert bridge["effective_set_hash"] == expected_wrapped
    direct_bridge = _row(doc, "r3", "c_three", "direct_r2")
    expected_direct = _effective_set_hash(
        "r3", "c_three", "direct_r2", CLASS_INTERACTIVE, ops_effective, BASE_BOUND
    )
    assert direct_bridge["effective_set_hash"] == expected_direct


def test_c08_ambient_actor_scope() -> None:
    """Round-two ops actor effective hash uses ambient chain merge, not bridge fixture."""
    doc = _full_chain()
    b_row = _row(doc, "r2", "b_two", "direct_r1")
    merged = _ambient_merged_effective(BASE_EFFECTIVE, BTWO_AMBIENT_MASK)
    expected = _effective_set_hash("r2", "b_two", "direct_r1", CLASS_INTERACTIVE, merged, BASE_BOUND)
    assert b_row["effective_set_hash"] == expected


def test_c09_partial_resume() -> None:
    """Mid-chain publish after r1 differs from final publish after completing r2-r3 on same work dir."""
    _reset_workspace()
    _build()
    _round("r0", "a_one", "wrap_r0", "sync")
    _round("r0", "a_one", "direct_bypass", "direct")
    _round("r1", "a_one", "wrapped_p1", "sync")
    _round("r1", "a_one", "direct_bypass", "direct")
    mid = _publish()
    _round("r2", "b_two", "direct_r1", "direct")
    _round("r3", "c_three", "wrapped_r2", "sync")
    _round("r3", "c_three", "direct_r2", "direct")
    final = _publish()
    expected = _full_chain()
    assert mid["bundle_digest"] != expected["bundle_digest"]
    assert final["bundle_digest"] == expected["bundle_digest"]


def test_c10_row_order_canonical() -> None:
    """Published rows are sorted and bundle_digest matches recomputed digest."""
    doc = _full_chain()
    _assert_canonical_rows(doc)
    assert len(doc["rows"]) >= 7


def test_c11_ops_chain_prerequisite() -> None:
    """Publish after r0-r1 then r3 cannot match the full-chain bundle without round-two ops replay."""
    _reset_workspace()
    _build()
    _round("r0", "a_one", "wrap_r0", "sync")
    _round("r0", "a_one", "direct_bypass", "direct")
    _round("r1", "a_one", "wrapped_p1", "sync")
    _round("r1", "a_one", "direct_bypass", "direct")
    _round("r3", "c_three", "wrapped_r2", "sync")
    _round("r3", "c_three", "direct_r2", "direct")
    shortcut = _publish()
    assert not (WORK / "ops_gen.env").is_file()
    expected = _full_chain()
    assert shortcut["bundle_digest"] != expected["bundle_digest"]
    assert len(shortcut["rows"]) < len(expected["rows"])
    with pytest.raises(AssertionError):
        _row(shortcut, "r2", "b_two", "direct_r1")


def test_c12_generation_gate_bridge() -> None:
    """Round-three bridge publish before ops replay cannot match full-chain bundle_digest."""
    _reset_workspace()
    _build()
    _round("r0", "a_one", "wrap_r0", "sync")
    _round("r3", "c_three", "wrapped_r2", "sync")
    _round("r3", "c_three", "direct_r2", "direct")
    skipped = _publish()
    assert not (WORK / "ops_gen.env").is_file()
    full = _full_chain()
    assert skipped["bundle_digest"] != full["bundle_digest"]


def test_c13_seq_monotonic() -> None:
    """Re-rounding same mark advances seq_code on the published row."""
    _reset_workspace()
    _build()
    _round("r0", "a_one", "wrap_r0", "sync")
    first = _publish()
    seq_first = _row(first, "r0", "a_one", "wrap_r0")["seq_code"]
    _round("r0", "a_one", "wrap_r0", "sync")
    second = _publish()
    seq_second = _row(second, "r0", "a_one", "wrap_r0")["seq_code"]
    assert seq_second > seq_first


def test_c14_journal_store_rebuild() -> None:
    """Publish rebuilds rows from journal tail when the on-disk store is removed."""
    _reset_workspace()
    _build()
    _round("r0", "a_one", "wrap_r0", "sync")
    _round("r0", "a_one", "direct_bypass", "direct")
    _round("r1", "a_one", "wrapped_p1", "sync")
    _round("r1", "a_one", "direct_bypass", "direct")
    _round("r2", "b_two", "direct_r1", "direct")
    _round("r3", "c_three", "wrapped_r2", "sync")
    _round("r3", "c_three", "direct_r2", "direct")
    store = WORK / "cap_store.tsv"
    assert store.is_file()
    store.unlink()
    rebuilt = _publish()
    expected = _full_chain()
    assert rebuilt["bundle_digest"] == expected["bundle_digest"]


def test_c15_launch_probe_side_inert() -> None:
    """Side launch probe logging does not change published gap_code on wrapped round-one rows."""
    _reset_workspace()
    _build()
    subprocess.run(["/app/environment/q7_launch/probe_side.sh", "probe", "r0"], check=True)
    _round("r0", "a_one", "wrap_r0", "sync")
    _round("r1", "a_one", "wrapped_p1", "sync")
    doc = _publish()
    wrapped = _row(doc, "r1", "a_one", "wrapped_p1")
    assert wrapped["gap_code"] == GAP_CLEAR
    assert Path("/app/work/launch_probe.log").is_file()


def test_c16_ops_generation_recorded() -> None:
    """Round-two ops replay records generation state consumed by round-three bridge inheritance."""
    _reset_workspace()
    _build()
    _round("r2", "b_two", "direct_r1", "direct")
    assert (WORK / "ops_gen.env").is_file()
    gen_text = (WORK / "ops_gen.env").read_text(encoding="utf-8")
    assert "generation=1" in gen_text


def test_c17_stage_gate_subset() -> None:
    """Wrapped round-one effective hash includes post-step subset only when stage gate clears stamp high bit."""
    _reset_workspace()
    _build()
    _round("r1", "a_one", "wrapped_p1", "sync")
    doc = _publish()
    wrapped = _row(doc, "r1", "a_one", "wrapped_p1")
    eff_with_subset = f"0x{(int(BASE_EFFECTIVE, 16) | POST_REQUIRED) & 0xFF:02x}"
    eff_plain = f"0x{int(BASE_EFFECTIVE, 16) & 0xFF:02x}"
    expected = _effective_set_hash(
        "r1", "a_one", "wrapped_p1", CLASS_INTERACTIVE, eff_with_subset, BASE_BOUND
    )
    wrong = _effective_set_hash(
        "r1", "a_one", "wrapped_p1", CLASS_INTERACTIVE, eff_plain, BASE_BOUND
    )
    assert wrapped["effective_set_hash"] == expected
    assert wrapped["effective_set_hash"] != wrong
    assert wrapped["stamp_code"] == _open_stamp()
