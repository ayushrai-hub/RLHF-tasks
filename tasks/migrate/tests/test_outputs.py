"""Exact-match verification of version-control build plan over every held-out program."""
import pathlib

import pytest

OUT = pathlib.Path("/app/out")
EXPECTED = pathlib.Path(__file__).parent / "expected"
CASES = sorted(p.stem for p in EXPECTED.glob("*.txt"))


def _read(p):
    return p.read_text() if p.exists() else None


def test_out_dir_exists():
    assert OUT.is_dir(), "/app/out must exist"


def test_all_outputs_present():
    missing = [c for c in CASES if not (OUT / f"{c}.txt").exists()]
    assert not missing, f"missing outputs: {missing}"


@pytest.mark.parametrize("case", CASES)
def test_case_exact_match(case):
    got = _read(OUT / f"{case}.txt")
    want = _read(EXPECTED / f"{case}.txt")
    assert got == want, f"{case}: output mismatch\n--- expected ---\n{want}\n--- got ---\n{got}"
