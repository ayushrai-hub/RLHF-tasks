import json
import shutil
import subprocess
from pathlib import Path

import pytest

APP = Path("/app")
ENV = APP / "environment"
FIX_PRACTICE = ENV / "fixtures" / "practice"
FIX_REG = ENV / "fixtures" / "regression"
AUDIT_CMD = "/app/bin/registeraudit"
REPORT_PATH = APP / "out" / "mreg_audit.json"
TIP_PATH = APP / "out" / ".mregtip"
CONTINUE_TIP = "a" * 64
RECOMPUTE = Path("/tests/mreg_audit_recompute.py")

REPORT_KEYS = frozenset(
    {
        "api_version",
        "segment",
        "mreg_files",
        "frame_count",
        "register_read_count",
        "crc_failure_count",
        "exception_count",
        "chain_root_hex",
        "duplicate_seq_drops",
        "slave_reject_count",
        "checkpoint_skip_count",
        "min_reg",
        "max_reg",
        "active_slave_count",
    }
)


def _rebuild_binary() -> None:
    proc = subprocess.run(
        [
            "go",
            "build",
            "-C",
            "/app/environment",
            "-o",
            "/app/bin/registeraudit",
            "/app/environment/cmd/registeraudit",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    assert Path(AUDIT_CMD).is_file()


@pytest.fixture(scope="session", autouse=True)
def _audit_binary_built() -> None:
    _rebuild_binary()


def _reset_out() -> None:
    out_dir = APP / "out"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)


def _recompute(mreg_dir: Path, segment: int, *, tip_hex: str | None = None) -> dict:
    cmd = ["python3", str(RECOMPUTE), str(mreg_dir), str(segment)]
    if tip_hex is not None:
        cmd.append(tip_hex)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    return json.loads(proc.stdout)


def _run_audit(
    mreg_dir: Path,
    segment: int,
    *,
    tip_hex: str | None = None,
) -> dict:
    _reset_out()
    if tip_hex is not None:
        TIP_PATH.write_text(tip_hex, encoding="utf-8")
    proc = subprocess.run(
        [
            AUDIT_CMD,
            "audit",
            "-mreg-dir",
            str(mreg_dir),
            "-segment",
            str(segment),
            "-json-out",
            str(REPORT_PATH),
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    raw = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(raw, dict), "report must be a JSON object at top level"
    assert "debug" not in raw, "report must not be wrapped in a debug envelope"
    return raw


def _assert_contract(
    report: dict,
    mreg_dir: Path,
    segment: int,
    *,
    tip_hex: str | None = None,
) -> None:
    ref = _recompute(mreg_dir, segment, tip_hex=tip_hex)
    assert set(report.keys()) == REPORT_KEYS
    assert report == ref


def test_practice_segment_three_matches_contract() -> None:
    """Practice capture tree at segment 3 matches independent contract recomputation."""
    report = _run_audit(FIX_PRACTICE, 3)
    _assert_contract(report, FIX_PRACTICE, 3)


def test_mregorder_overlay_applied() -> None:
    """Practice scans honor .mregorder priority when listing capture files."""
    report = _run_audit(FIX_PRACTICE, 3)
    assert report["mreg_files"] == ["beta.mreg", "alpha.mreg"]


def test_crc_noise_excludes_bad_checksum() -> None:
    """CRC-invalid frames increment crc_failure_count and skip chain walks."""
    report = _run_audit(FIX_REG / "crc_noise", 1)
    assert report["crc_failure_count"] == 1
    _assert_contract(report, FIX_REG / "crc_noise", 1)


def test_duplicate_seq_last_frame_wins() -> None:
    """Repeated sequence ids keep the later shard row."""
    report = _run_audit(FIX_REG / "duplicate_seq", 2)
    _assert_contract(report, FIX_REG / "duplicate_seq", 2)


def test_slave_reject_excluded_from_chain() -> None:
    """Unknown slave ids increment slave_reject_count and skip the row."""
    report = _run_audit(FIX_REG / "slave_reject", 1)
    _assert_contract(report, FIX_REG / "slave_reject", 1)


def test_checkpoint_marker_skipped() -> None:
    """Checkpoint markers are omitted from totals and chain walks."""
    report = _run_audit(FIX_REG / "checkpoint_skip", 1)
    _assert_contract(report, FIX_REG / "checkpoint_skip", 1)


def test_order_overlay_sidecar() -> None:
    """Regression overlay honors .mregorder file priority."""
    report = _run_audit(FIX_REG / "order_overlay", 1)
    _assert_contract(report, FIX_REG / "order_overlay", 1)


def test_empty_scan_zero_state() -> None:
    """Directory without capture shards yields zeroed counters."""
    report = _run_audit(FIX_REG / "empty_scan", 1)
    _assert_contract(report, FIX_REG / "empty_scan", 1)


def test_continue_seed_without_tip_uses_zero_seed() -> None:
    """Continuation marker alone does not read unrelated output tips."""
    report = _run_audit(FIX_REG / "continue_seed", 5)
    _assert_contract(report, FIX_REG / "continue_seed", 5)


def test_continue_seed_with_tip_extends_chain() -> None:
    """Continuation scans seed from /app/out/.mregtip when marker present."""
    report = _run_audit(FIX_REG / "continue_seed", 5, tip_hex=CONTINUE_TIP)
    _assert_contract(report, FIX_REG / "continue_seed", 5, tip_hex=CONTINUE_TIP)


def test_unrelated_stale_tip_ignored_on_practice_scan() -> None:
    """Practice scans without .mreg_continue ignore /app/out/.mregtip."""
    _reset_out()
    TIP_PATH.write_text("f" * 64, encoding="utf-8")
    report = _run_audit(FIX_PRACTICE, 3)
    ref = _recompute(FIX_PRACTICE, 3)
    assert report["chain_root_hex"] == ref["chain_root_hex"]


def test_mregtip_written_after_successful_audit() -> None:
    """Final chain root is persisted beside the JSON report directory."""
    report = _run_audit(FIX_PRACTICE, 3)
    assert TIP_PATH.is_file()
    assert TIP_PATH.read_text(encoding="utf-8").strip() == report["chain_root_hex"]


def test_output_regenerated_not_static() -> None:
    """Deleting prior output and rerunning reproduces the practice digest."""
    first = _run_audit(FIX_PRACTICE, 3)
    assert REPORT_PATH.exists()
    REPORT_PATH.unlink()
    second = _run_audit(FIX_PRACTICE, 3)
    assert second["chain_root_hex"] == first["chain_root_hex"]
