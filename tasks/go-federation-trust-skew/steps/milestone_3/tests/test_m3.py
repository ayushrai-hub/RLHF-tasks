import json
import subprocess
from pathlib import Path

import pytest

ENV_DIR = Path("/app/environment")
WARD_PKG = "/app/environment/internal/ward/"
M1 = "TestWard_T01|TestWard_T02|TestWard_T03|TestWard_T04|TestWard_T05|TestWard_T06|TestWard_T07|TestWard_T08"
M2 = "TestWard_T09|TestWard_T10|TestWard_T11|TestWard_T12|TestWard_T13|TestWard_T14|TestWard_T15|TestWard_T16|TestWard_T34|TestWard_T35"
BIND_CASES = [f"T{n:02d}" for n in range(17, 34)]
EXT_CASES = [f"T{n:02d}" for n in range(25, 37)]
EXACT_GRADED_PASSES = 38
GRADE_SHA = "bb166fd86ef375a17e7dc847e84f69ae9f1b50641f59003e6e9765f0c80ed05d"


def _run_go_test(pattern: str, race: bool = False, count: int = 1) -> subprocess.CompletedProcess:
    cmd = ["go", "test", WARD_PKG, "-v", "-run", pattern, f"-count={count}"]
    if race:
        cmd.insert(2, "-race")
    timeout = 600 if race else 300
    return subprocess.run(cmd, cwd=str(ENV_DIR), capture_output=True, text=True, timeout=timeout)


def _go_test_should_pass(pattern: str, race: bool = False, count: int = 1) -> str:
    result = _run_go_test(pattern, race=race, count=count)
    assert result.returncode == 0, (
        f"go test -run {pattern} FAILED:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "--- PASS:" in result.stdout
    assert "FAIL" not in result.stdout
    return result.stdout


def _count_passes(stdout: str) -> int:
    return stdout.count("--- PASS:")


@pytest.mark.parametrize("case_id", BIND_CASES)
def test_m3_binding_cases(case_id: str):
    """Graded realm binding cases must pass."""
    out = _go_test_should_pass(f"TestWard_{case_id}")
    assert _count_passes(out) == 1


@pytest.mark.parametrize("case_id", EXT_CASES)
def test_m3_ext_id_cases(case_id: str):
    """Graded external id cases must pass."""
    out = _go_test_should_pass(f"TestWard_{case_id}")
    assert _count_passes(out) == 1


def test_full_graded_suite():
    """Complete graded suite must pass with exact case volume."""
    result = subprocess.run(
        ["go", "test", WARD_PKG, "-v", "-count=1"],
        cwd=str(ENV_DIR),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, (
        f"full suite failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "FAIL" not in result.stdout
    assert _count_passes(result.stdout) == EXACT_GRADED_PASSES


def test_probe_fresh_path():
    """Serial fresh assertion probe path must admit."""
    _go_test_should_pass("TestWard_ProbeFresh")


def test_race_reload_subset():
    """Concurrent reload subset must not return stale principals."""
    _go_test_should_pass("TestWard_RaceReload")


@pytest.mark.parametrize("repeat", [1, 2])
def test_m1_regression(repeat: int):
    """Milestone 1 window fixes must remain intact."""
    _go_test_should_pass(M1, count=repeat)


@pytest.mark.parametrize("repeat", [1, 2])
def test_m2_regression(repeat: int):
    """Milestone 2 bundle fixes must remain intact."""
    _go_test_should_pass(M2, count=repeat)


def test_harness_output_script():
    """Harness script must exit zero after regeneration."""
    result = subprocess.run(
        ["bash", "/app/environment/scripts/verify_output.sh"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr


def test_harness_status_regenerated():
    """Harness status file must be rewritten by verify_output.sh."""
    status = Path("/app/output/harness/status.txt")
    assert status.exists()
    assert status.read_text().strip() == "harness_ok"


def test_probe_json_schema():
    """Probe JSON must expose ready, code, and principal fields."""
    subprocess.run(["/app/bin/probe"], check=True, timeout=60)
    probe = Path("/app/output/stage/probe.json")
    assert probe.exists()
    data = json.loads(probe.read_text())
    assert data["ready"] is True
    assert data["code"] == "ADMIT"
    assert isinstance(data.get("principal"), str) and data["principal"]


def test_build_all_packages():
    """Full workspace build must succeed after alias fixes."""
    result = subprocess.run(
        ["go", "build", "/app/environment/..."],
        cwd=str(ENV_DIR),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr


def test_graded_suite_integrity():
    """Hidden checker source must remain unchanged (SHA256 integrity gate)."""
    res = subprocess.run(
        ["sha256sum", "/app/environment/internal/ward/m4_grade_test.go"],
        capture_output=True,
        text=True,
        check=True,
    )
    digest = res.stdout.split()[0]
    assert digest == GRADE_SHA
