import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

APP = Path("/app")
ENV = APP / "environment"
OUT_REPORT = APP / "output" / "run_report.json"
CMD = ["/app/environment/cmd/verify_k9", "--matrix-full"]
TC_MNT = ENV / "fixtures/blk/tc.mnt"
TD_MNT = ENV / "fixtures/blk/td.mnt"
P9_STUB = ENV / "fixtures/q9/p9_stub.json"
EPOCH = ENV / "meta/epoch.marker"
EMIT_CEILING = 3
ANCHOR = Path("/tmp/fvr_anchor.bin")
HASH_TOOL = ENV / "scripts/contract_hash.py"
_ORIG_EPOCH = EPOCH.read_text()


def _restore_epoch():
    EPOCH.write_text(_ORIG_EPOCH)


@pytest.fixture(autouse=True)
def _epoch_reset():
    _restore_epoch()
    yield
    _restore_epoch()


def _canonical_rows() -> list[dict]:
    return [
        {
            "slot_id": 1,
            "parent_slot": 0,
            "attach_path": "/mnt/a",
            "option_map": {"opts": "rw,relatime"},
            "band_class": 1,
        },
        {
            "slot_id": 2,
            "parent_slot": 1,
            "attach_path": "/mnt/y",
            "option_map": {"opts": "bind,shared"},
            "band_class": 2,
        },
        {
            "slot_id": 3,
            "parent_slot": 2,
            "attach_path": "/mnt/b",
            "option_map": {"opts": "rw,relatime"},
            "band_class": 1,
        },
    ]


def _blk_anchor_hex(path: Path) -> str:
    return path.read_bytes()[:32].hex()


def _opt_digest(opt: dict) -> str:
    return hashlib.sha256(json.dumps(opt, sort_keys=True).encode()).hexdigest()[:8]


def _digest_from_tuples(rows: list[dict], blk_path: Path) -> str:
    parts = []
    for item in sorted(rows, key=lambda r: r["slot_id"]):
        od = _opt_digest(item["option_map"])
        parts.append(
            f"{item['slot_id']}|{item['parent_slot']}|{item['attach_path']}|"
            f"{item['band_class']}|{od}"
        )
    payload = "\n".join(parts) + "|" + _blk_anchor_hex(blk_path)
    return hashlib.sha256(payload.encode()).hexdigest()[:8]


def _run_checker() -> dict:
    shutil.rmtree(APP / "output", ignore_errors=True)
    proc = subprocess.run(CMD, text=True, capture_output=True, timeout=120)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert OUT_REPORT.is_file()
    return json.loads(OUT_REPORT.read_text())


def _lane(report: dict, lane_id: str) -> dict:
    for rec in report["lane_records"]:
        if rec["lane_id"] == lane_id:
            return rec
    raise KeyError(lane_id)


def _digest_via_tool(rows: list[dict]) -> str:
    payload = json.dumps(rows)
    tmp = Path("/tmp/fvr_rows_probe.json")
    tmp.write_text(payload)
    out = subprocess.run(
        ["python3", str(HASH_TOOL), str(tmp), str(TC_MNT)],
        check=True,
        text=True,
        capture_output=True,
    )
    return out.stdout.strip()


def test_ladder_digest_tool_agrees():
    """contract_hash reproduces terminal_digest from pact_f2 canonical row tuples."""
    report = _run_checker()
    terminal = report["summary"]["terminal_digest"]
    assert _digest_via_tool(_canonical_rows()) == terminal


def test_ladder_k2_slave_profile_band():
    """lane_k2 lane_record band_class reflects unit slave-carry severity."""
    report = _run_checker()
    assert _lane(report, "lane_k2")["band_class"] == 3


def test_ladder_sparse_lane_corpus_converges():
    """lane_k2 sparse fragment list still converges to the lane_k1 baseline digest."""
    report = _run_checker()
    base = _lane(report, "lane_k1")["state_digest"]
    sparse = _lane(report, "lane_k2")["state_digest"]
    assert sparse == base
    assert base == report["summary"]["terminal_digest"]


def test_ladder_summary_emit_ceiling():
    """summary row_count matches digest_emit_ceiling emitted rows, not corpus width."""
    report = _run_checker()
    assert report["summary"]["row_count"] == EMIT_CEILING
    assert report["schema_version"] == 1
    assert report["command"] == "verify_k9 --matrix-full"


def test_ladder_slot4_excluded_from_digest():
    """overflow slot_id 4 from frag_b.tab must not enter digest tuples."""
    report = _run_checker()
    terminal = report["summary"]["terminal_digest"]
    overflow = _canonical_rows() + [
        {
            "slot_id": 4,
            "parent_slot": 2,
            "attach_path": "/mnt/w",
            "option_map": {"opts": "rw,relatime"},
            "band_class": 1,
        }
    ]
    assert _digest_via_tool(overflow) != terminal


def test_ladder_workdir_scoring_k3_converges():
    """lane_k3 td.mnt workdir scoring still converges to the tc.mnt digest baseline."""
    report = _run_checker()
    base = _lane(report, "lane_k1")["state_digest"]
    k3 = _lane(report, "lane_k3")["state_digest"]
    assert k3 == base
    assert _blk_anchor_hex(TD_MNT) != _blk_anchor_hex(TC_MNT)


def test_ladder_bind_reloc_canonical_path():
    """bind relocation keeps slot 2 on /mnt/y; stale /mnt/z tuples mismatch terminal."""
    report = _run_checker()
    terminal = report["summary"]["terminal_digest"]
    stale_bind = [
        {
            "slot_id": 1,
            "parent_slot": 0,
            "attach_path": "/mnt/a",
            "option_map": {"opts": "rw,relatime"},
            "band_class": 1,
        },
        {
            "slot_id": 2,
            "parent_slot": 1,
            "attach_path": "/mnt/z",
            "option_map": {"opts": "bind,shared"},
            "band_class": 2,
        },
        {
            "slot_id": 3,
            "parent_slot": 2,
            "attach_path": "/mnt/b",
            "option_map": {"opts": "rw,relatime"},
            "band_class": 1,
        },
    ]
    assert _digest_via_tool(stale_bind) != terminal
    assert _digest_via_tool(_canonical_rows()) == terminal


def test_ladder_duplicate_recovery_zero_drift():
    """lane_k4 duplicate recovery keeps state_digest aligned with the baseline."""
    report = _run_checker()
    base = _lane(report, "lane_k1")["state_digest"]
    dup = _lane(report, "lane_k4")["state_digest"]
    assert dup == base
    again = _run_checker()["summary"]["terminal_digest"]
    assert again == base


def test_ladder_q9_anchor_recovery_preserves_digest():
    """q9_clear plus arena_seed anchor restore preserves terminal_digest across epoch bump."""
    before = _run_checker()["summary"]["terminal_digest"]
    subprocess.run(["bash", str(ENV / "ops/q9_clear.sh")], check=True, timeout=30)
    shutil.copy(ENV / "fixtures/seed/arena_seed.bin", ANCHOR)
    after = _run_checker()["summary"]["terminal_digest"]
    assert after == before
    assert int(EPOCH.read_text()) == int(_ORIG_EPOCH) + 1
    assert ANCHOR.read_bytes() == (ENV / "fixtures/seed/arena_seed.bin").read_bytes()


def test_ladder_p9_interim_rows_decoy():
    """p9_stub interim rows are diagnostic only and do not reproduce terminal_digest."""
    report = _run_checker()
    stub = json.loads(P9_STUB.read_text())
    decoy = [
        {
            "slot_id": row["slot_id"],
            "parent_slot": 0,
            "attach_path": row["attach_path"],
            "option_map": {"opts": "rw"},
            "band_class": row["band_class"],
        }
        for row in stub["interim_rows"]
    ]
    assert _digest_from_tuples(decoy, TC_MNT) != report["summary"]["terminal_digest"]


def test_ladder_slave_opts_stripped_before_digest():
    """consumer emission strips slave from digest tuples even when unit carries slave."""
    report = _run_checker()
    terminal = report["summary"]["terminal_digest"]
    unstripped = [
        {
            "slot_id": 1,
            "parent_slot": 0,
            "attach_path": "/mnt/a",
            "option_map": {"opts": "rw,relatime"},
            "band_class": 1,
        },
        {
            "slot_id": 2,
            "parent_slot": 1,
            "attach_path": "/mnt/y",
            "option_map": {"opts": "bind,shared"},
            "band_class": 2,
        },
        {
            "slot_id": 3,
            "parent_slot": 2,
            "attach_path": "/mnt/b",
            "option_map": {"opts": "rw,slave"},
            "band_class": 3,
        },
    ]
    assert _digest_via_tool(unstripped) != terminal
