import subprocess
from pathlib import Path

import pytest

ENV_DIR = Path("/app/environment")
WARD_PKG = "/app/environment/internal/ward/"
M1 = "TestWard_T01|TestWard_T02|TestWard_T03|TestWard_T04|TestWard_T05|TestWard_T06|TestWard_T07|TestWard_T08"
M2 = "TestWard_T09|TestWard_T10|TestWard_T11|TestWard_T12|TestWard_T13|TestWard_T14|TestWard_T15|TestWard_T16|TestWard_T34|TestWard_T35"
GRADE_SHA = "bb166fd86ef375a17e7dc847e84f69ae9f1b50641f59003e6e9765f0c80ed05d"


def _run_go_test(pattern: str, count: int = 1) -> subprocess.CompletedProcess:
    cmd = ["go", "test", WARD_PKG, "-v", "-run", pattern, f"-count={count}"]
    return subprocess.run(cmd, cwd=str(ENV_DIR), capture_output=True, text=True, timeout=180)


def _go_test_should_pass(pattern: str, count: int = 1) -> str:
    result = _run_go_test(pattern, count=count)
    assert result.returncode == 0, (
        f"go test -run {pattern} FAILED:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "--- PASS:" in result.stdout
    assert "FAIL" not in result.stdout
    return result.stdout


@pytest.mark.parametrize("case_id", [f"T{n:02d}" for n in range(9, 17)] + ["T34", "T35"])
def test_m2_bundle_cases(case_id: str):
    """Graded bundle generation cases must pass."""
    out = _go_test_should_pass(f"TestWard_{case_id}")
    assert out.count("--- PASS:") == 1


@pytest.mark.parametrize("count", [1, 2])
def test_m2_bundle_matrix(count: int):
    """Bundle scenarios must pass at multiple repetition counts."""
    _go_test_should_pass(M2, count=count)


@pytest.mark.parametrize("repeat", [1, 2])
def test_m1_regression(repeat: int):
    """Milestone 1 window fixes must remain intact."""
    _go_test_should_pass(M1, count=repeat)


@pytest.mark.parametrize("case_id", ["T02", "T04", "T08"])
def test_m1_regression_spot_checks(case_id: str):
    """Spot-check milestone 1 cases during milestone 2 verification."""
    _go_test_should_pass(f"TestWard_{case_id}")


def test_build_workspace():
    """The ward workspace must compile after bundle fixes."""
    result = subprocess.run(
        ["go", "build", "/app/environment/..."],
        cwd=str(ENV_DIR),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr


def test_spool_modules_present():
    """Bundle store modules must remain in the tree."""
    assert Path("/app/environment/tally/spool/eligible.go").is_file()
    assert Path("/app/environment/tally/spool/select.go").is_file()


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
