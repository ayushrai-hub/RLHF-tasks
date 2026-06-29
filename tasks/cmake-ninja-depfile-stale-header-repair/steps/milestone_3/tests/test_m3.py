"""Tests for milestone 3 — build audit parses Ninja log after touch replay."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reference_audit import expected_rebuilt_after_offset, load_fixture

APP = Path("/app")
BUILD = APP / "build"
AUDIT_SCRIPT = APP / "scripts" / "build_audit.py"
HIDDEN_FIXTURE = Path("/tests/hidden_touch_order.json")
HIDDEN_FIXTURE_B = Path("/tests/hidden_touch_order_b.json")
HIDDEN_FIXTURE_C = Path("/tests/hidden_touch_order_c.json")
PUBLIC_FIXTURE = APP / "fixtures" / "touch_order.json"
OUTPUT = APP / "output" / "build_audit.json"
PUBLIC_OUTPUT = APP / "output" / "public_audit.json"
NINJA_LOG = BUILD / ".ninja_log"

REQUIRED_KEYS = {"schema_version", "workload_id", "touch_count", "rebuilt_targets"}

HIDDEN_FIXTURE_SHA256 = (
    "8e6354cea43ef5a8248e842d44d5cde5ab649549e227150094558d05556db591"
)
HIDDEN_FIXTURE_B_SHA256 = (
    "11f2cb771ce948a17932caef53bf16c650103e945cdbf56bcead089210b179c6"
)
HIDDEN_FIXTURE_C_SHA256 = (
    "0530a235d67671de83cc383ca21430c9ada151d757187ab332000bad97e10a45"
)


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(APP), capture_output=True, text=True, check=False)


def _fixture_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_report_matches_log_window(report: dict, start_offset: int) -> None:
    """Report must equal log-derived rebuilds and contain only post-offset paths."""
    expected = expected_rebuilt_after_offset(start_offset)
    assert report["rebuilt_targets"] == expected, (
        f"audit {report['rebuilt_targets']} != log-derived {expected}"
    )
    assert report["rebuilt_targets"] == sorted(set(report["rebuilt_targets"]))


class TestMilestone3:
    """Audit CLI must derive rebuilt_targets from Ninja log with absolute-path guards."""

    def test_hidden_fixture_checksum(self) -> None:
        """Hidden grading fixture must match pinned bytes (anti-tamper)."""
        assert HIDDEN_FIXTURE.is_file(), "missing hidden fixture"
        assert _fixture_sha256(HIDDEN_FIXTURE) == HIDDEN_FIXTURE_SHA256

    def test_hidden_fixture_b_checksum(self) -> None:
        """Secondary hidden fixture must match pinned bytes (anti-tamper)."""
        assert HIDDEN_FIXTURE_B.is_file(), "missing hidden fixture B"
        assert _fixture_sha256(HIDDEN_FIXTURE_B) == HIDDEN_FIXTURE_B_SHA256

    def test_hidden_fixture_c_checksum(self) -> None:
        """Fence-only hidden fixture must match pinned bytes (anti-tamper)."""
        assert HIDDEN_FIXTURE_C.is_file(), "missing hidden fixture C"
        assert _fixture_sha256(HIDDEN_FIXTURE_C) == HIDDEN_FIXTURE_C_SHA256

    def test_relative_fixture_path_rejected(self) -> None:
        """Non-absolute fixture paths must fail with absolute on stderr."""
        proc = _run(
            [
                "python3",
                str(AUDIT_SCRIPT),
                "--fixture",
                "fixtures/touch_order.json",
                "--output",
                str(OUTPUT),
            ]
        )
        assert proc.returncode != 0
        assert "absolute" in (proc.stderr or "").lower()

    def test_relative_output_path_rejected(self) -> None:
        """Non-absolute output paths must fail with absolute on stderr."""
        proc = _run(
            [
                "python3",
                str(AUDIT_SCRIPT),
                "--fixture",
                str(PUBLIC_FIXTURE),
                "--output",
                "output/relative_audit.json",
            ]
        )
        assert proc.returncode != 0
        assert "absolute" in (proc.stderr or "").lower()

    def test_missing_touch_path_rejected(self) -> None:
        """Fixture entries pointing at missing files must exit non-zero."""
        bad = APP / "output" / "bad_fixture.json"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "workload_id": "missing-path-probe",
                    "touch_entries": [
                        {
                            "path": "/app/include/depfix/does_not_exist.hpp",
                            "token": "missing",
                        }
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        proc = _run(
            [
                "python3",
                str(AUDIT_SCRIPT),
                "--fixture",
                str(bad),
                "--output",
                str(OUTPUT),
            ]
        )
        assert proc.returncode != 0

    def test_util_depends_on_header_sync_before_audit(self) -> None:
        """Header sync wiring must be present so util rebuilds come from the stamp graph."""
        query = _run(["ninja", "-C", str(BUILD), "-t", "query", "libdepfix_util.a"])
        assert query.returncode == 0, query.stderr
        assert "depfix_header_sync" in query.stdout, query.stdout

    def test_public_fixture_audit_matches_ninja_log(self) -> None:
        """Public fixture audit output must match independently parsed ninja log."""
        PUBLIC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        if PUBLIC_OUTPUT.exists():
            PUBLIC_OUTPUT.unlink()
        offset = NINJA_LOG.stat().st_size if NINJA_LOG.exists() else 0
        proc = _run(
            [
                "python3",
                str(AUDIT_SCRIPT),
                "--fixture",
                str(PUBLIC_FIXTURE),
                "--output",
                str(PUBLIC_OUTPUT),
            ]
        )
        assert proc.returncode == 0, proc.stderr
        report = json.loads(PUBLIC_OUTPUT.read_text(encoding="utf-8"))
        _assert_report_matches_log_window(report, offset)

    def test_hidden_fixture_audit_matches_ninja_log(self) -> None:
        """Hidden fixture audit output must match Ninja log entries from the audit run."""
        fixture = load_fixture(HIDDEN_FIXTURE)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        if OUTPUT.exists():
            OUTPUT.unlink()

        log_offset = NINJA_LOG.stat().st_size if NINJA_LOG.exists() else 0

        proc = _run(
            [
                "python3",
                str(AUDIT_SCRIPT),
                "--fixture",
                str(HIDDEN_FIXTURE),
                "--output",
                str(OUTPUT),
            ]
        )
        assert proc.returncode == 0, proc.stderr

        raw = OUTPUT.read_text(encoding="utf-8")
        assert raw.endswith("\n"), "audit JSON must end with trailing newline"
        report = json.loads(raw)
        assert set(report.keys()) == REQUIRED_KEYS
        assert report["schema_version"] == 1
        assert report["workload_id"] == fixture["workload_id"]
        assert report["touch_count"] == len(fixture["touch_entries"])
        assert isinstance(report["rebuilt_targets"], list)

        _assert_report_matches_log_window(report, log_offset)
        assert any("depfix_core.dir/src/core.cpp.o" in p for p in report["rebuilt_targets"])
        assert any("depfix_util.dir/src/util.cpp.o" in p for p in report["rebuilt_targets"])

    def test_hidden_fixture_b_audit_matches_ninja_log(self) -> None:
        """Secondary hidden fixture must replay tokens and match the ninja log."""
        alt_output = APP / "output" / "build_audit_b.json"
        alt_output.parent.mkdir(parents=True, exist_ok=True)
        if alt_output.exists():
            alt_output.unlink()
        log_offset = NINJA_LOG.stat().st_size if NINJA_LOG.exists() else 0
        proc = _run(
            [
                "python3",
                str(AUDIT_SCRIPT),
                "--fixture",
                str(HIDDEN_FIXTURE_B),
                "--output",
                str(alt_output),
            ]
        )
        assert proc.returncode == 0, proc.stderr
        report = json.loads(alt_output.read_text(encoding="utf-8"))
        _assert_report_matches_log_window(report, log_offset)
        assert any("depfix_util.dir/src/util.cpp.o" in p for p in report["rebuilt_targets"])

    def test_hidden_fixture_c_fence_touch_matches_log(self) -> None:
        """Fence-only hidden fixture must rebuild core object without stale log bleed."""
        fence_output = APP / "output" / "build_audit_c.json"
        fence_output.parent.mkdir(parents=True, exist_ok=True)
        if fence_output.exists():
            fence_output.unlink()
        log_offset = NINJA_LOG.stat().st_size if NINJA_LOG.exists() else 0
        proc = _run(
            [
                "python3",
                str(AUDIT_SCRIPT),
                "--fixture",
                str(HIDDEN_FIXTURE_C),
                "--output",
                str(fence_output),
            ]
        )
        assert proc.returncode == 0, proc.stderr
        report = json.loads(fence_output.read_text(encoding="utf-8"))
        _assert_report_matches_log_window(report, log_offset)
        assert any("depfix_core.dir/src/core.cpp.o" in p for p in report["rebuilt_targets"])
