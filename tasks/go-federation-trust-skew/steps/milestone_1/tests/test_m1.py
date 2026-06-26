import subprocess
from pathlib import Path

import pytest

ENV_DIR = Path("/app/environment")
WARD_PKG = "/app/environment/internal/ward/"
M1 = "TestWard_T01|TestWard_T02|TestWard_T03|TestWard_T04|TestWard_T05|TestWard_T06|TestWard_T07|TestWard_T08"
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


@pytest.mark.parametrize("case_id", [f"T{n:02d}" for n in range(1, 9)])
def test_m1_time_window_cases(case_id: str):
    """Graded time-window cases T01–T08 must pass."""
    out = _go_test_should_pass(f"TestWard_{case_id}")
    assert out.count("--- PASS:") == 1


@pytest.mark.parametrize("count", [1, 2])
def test_m1_window_matrix(count: int):
    """Time window scenarios must pass at multiple repetition counts."""
    _go_test_should_pass(M1, count=count)


def test_build_workspace():
    """The ward workspace must compile after source fixes."""
    result = subprocess.run(
        ["go", "build", "/app/environment/..."],
        cwd=str(ENV_DIR),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr


def test_contract_docs_present():
    """Normative contract and API docs must remain available."""
    assert Path("/app/environment/docs/contract.md").is_file()
    assert Path("/app/environment/docs/api.md").is_file()


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


def test_chrono_modules_present():
    """Window helpers must remain part of the chrono and meter packages."""
    assert Path("/app/environment/chorus/chrono/bounds.go").is_file()
    assert Path("/app/environment/chorus/chrono/quantize.go").is_file()
    assert Path("/app/environment/meter/tolerance.go").is_file()
