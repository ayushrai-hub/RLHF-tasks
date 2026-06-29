import json
import os
import subprocess
from pathlib import Path


APP = Path("/app")
ENV = APP / "environment"
OUT = APP / "output" / "route_audit.json"
PROFILES = ("run_a", "run_b", "run_c", "run_d")
Q9_STUB = ENV / "fixtures" / "q9" / "p9_stub.json"
STATE_DIR = ENV / "var" / "state"
RUBY_ENV = {
    "RUBYLIB": ":".join(
        [
            str(ENV / "cmd"),
            str(ENV / "r7_lane"),
            str(ENV / "n4_cache"),
            str(ENV / "v8_scope"),
            str(ENV / "q3_trace"),
        ]
    )
}


def _reset_var():
    var_root = ENV / "var"
    if var_root.exists():
        for child in var_root.iterdir():
            if child.is_dir():
                for f in child.iterdir():
                    f.unlink(missing_ok=True)


def _digest_hex(path: Path) -> str:
    script = "require 'digest'; print Digest::SHA256.hexdigest(File.binread(ARGV[0]))"
    return subprocess.check_output(["ruby", "-e", script, str(path)], text=True).strip()


def _build_and_check() -> dict:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    _reset_var()
    subprocess.run(
        [
            "ruby",
            "/app/environment/cmd/var_check/main.rb",
            "--matrix-full",
            "--out",
            str(OUT),
        ],
        check=True,
        cwd=str(APP),
        env={**os.environ, **RUBY_ENV},
    )
    return json.loads(OUT.read_text(encoding="utf-8"))


def _runs_by_profile(report: dict) -> dict:
    grouped = {}
    for row in report["matrix_runs"]:
        grouped.setdefault(row["profile_key"], {})[row["path_kind"]] = row
    return grouped


def _fingerprints_agree(by: dict, key: str) -> None:
    assert (
        by[key]["uninterrupted"]["route_fingerprint"]
        == by[key]["recovered"]["route_fingerprint"]
    )


def test_m1_harness_exit_clean() -> None:
    """var_check exits 0 for all runs including held-out orderings."""
    report = _build_and_check()
    assert "matrix_runs" in report
    assert len(report["matrix_runs"]) == len(PROFILES) * 2


def test_m2_byte_bind_stable() -> None:
    """route_fingerprint matches sha256 of rebuilt canonical slice bytes."""
    report = _build_and_check()
    for row in report["matrix_runs"]:
        canonical = Path(row["canonical_path"])
        assert canonical.exists()
        assert row["route_fingerprint"] == _digest_hex(canonical)


def test_m3_public_smoke_guard() -> None:
    """Public run_a and run_b remain passing after generalization-oriented fixes."""
    report = _build_and_check()
    by = _runs_by_profile(report)
    for key in ("run_a", "run_b"):
        _fingerprints_agree(by, key)
        assert by[key]["recovered"]["internal_leak_count"] == 0


def test_m4_slot_obligations() -> None:
    """Held-out run_c fails if lane fixed without negative-bucket invalidation on slice load."""
    report = _build_and_check()
    by = _runs_by_profile(report)
    _fingerprints_agree(by, "run_c")


def test_m5_dual_path_rows() -> None:
    """Uninterrupted vs recovered paths agree on graded bytes, not q9-row-only surfaces."""
    report = _build_and_check()
    by = _runs_by_profile(report)
    for key in PROFILES:
        _fingerprints_agree(by, key)


def test_m6_interim_row_trap() -> None:
    """q9 interim rows alone do not satisfy terminal report grading."""
    stub = json.loads(Q9_STUB.read_text(encoding="utf-8"))
    assert isinstance(stub.get("interim_rows"), list)
    assert len(stub["interim_rows"]) >= 1
    report = _build_and_check()
    for row in report["matrix_runs"]:
        assert len(row["route_fingerprint"]) == 64
        assert row["internal_leak_count"] == 0


def test_m7_second_pass_guard() -> None:
    """Repeat migration without anchor preservation fails cross-cycle bands."""
    report = _build_and_check()
    run_d = _runs_by_profile(report)["run_d"]
    assert run_d["recovered"]["band_class"] <= 1
    _fingerprints_agree(_runs_by_profile(report), "run_d")


def test_m8_anchor_preserve_guard() -> None:
    """Documented recovery after migration preserves slice byte integrity."""
    report = _build_and_check()
    anchor = ENV / "var" / "anchor" / "lane.epoch"
    assert anchor.exists()
    for row in report["matrix_runs"]:
        if row["profile_key"] == "run_d" and row["path_kind"] == "recovered":
            _fingerprints_agree(_runs_by_profile(report), "run_d")
            slice_path = STATE_DIR / f"{row['profile_key']}_{row['path_kind']}.rt"
            assert len(slice_path.read_bytes()) >= 16
