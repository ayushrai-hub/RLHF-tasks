"""Milestone 3: cache stamps, head resolution, trace sidecar, and probe scenarios."""

from __future__ import annotations

from pathlib import Path

import pytest

from plate_common import (
    CACHE_GEN,
    CACHE_HEAD,
    clear_outputs,
    expected_for,
    expected_trace,
    get_pre_trim,
    install_probe_scenario,
    read_trace,
    run_driver,
    _get_dynamic_stamp,
)

PROBE_ROOT = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def _clear_outputs() -> None:
    clear_outputs()


class TestMilestone3:
    def test_preseeded_head_does_not_override_recompute(self) -> None:
        """Stale cache generation marker means cached head is ignored."""
        CACHE_HEAD.mkdir(parents=True, exist_ok=True)
        CACHE_GEN.mkdir(parents=True, exist_ok=True)
        (CACHE_HEAD / "tab_x.txt").write_text("9999", encoding="utf-8")
        (CACHE_GEN / "tab_x.txt").write_text("1", encoding="utf-8")
        got = run_driver("tab_x")
        assert got["head_seq"] == expected_for("tab_x")["head_seq"]

    def test_cached_head_stamp_applies_when_active(self) -> None:
        """Active cache may raise head_seq above the recomputed peak."""
        expected = expected_for("tab_x")
        stamp = _get_dynamic_stamp(expected["records_applied"])
        CACHE_HEAD.mkdir(parents=True, exist_ok=True)
        CACHE_GEN.mkdir(parents=True, exist_ok=True)
        (CACHE_HEAD / "tab_x.txt").write_text("9999", encoding="utf-8")
        (CACHE_GEN / "tab_x.txt").write_text(stamp, encoding="utf-8")
        got = run_driver("tab_x")
        assert got["head_seq"] == 9999

    def test_cached_head_does_not_lower_computed_peak(self) -> None:
        """Active cache must not lower head_seq below the recomputed peak."""
        expected = expected_for("tab_x")
        stamp = _get_dynamic_stamp(expected["records_applied"])
        CACHE_HEAD.mkdir(parents=True, exist_ok=True)
        CACHE_GEN.mkdir(parents=True, exist_ok=True)
        (CACHE_HEAD / "tab_x.txt").write_text("1", encoding="utf-8")
        (CACHE_GEN / "tab_x.txt").write_text(stamp, encoding="utf-8")
        got = run_driver("tab_x")
        assert got["head_seq"] == expected["head_seq"]

    def test_driver_persists_cache_after_run(self) -> None:
        """Driver run persists cache artifacts for the scenario."""
        got = run_driver("tab_x")
        gen_path = CACHE_GEN / "tab_x.txt"
        assert gen_path.is_file()
        expected_stamp = _get_dynamic_stamp(got["records_applied"])
        assert gen_path.read_text(encoding="utf-8").strip() == expected_stamp
        head = (CACHE_HEAD / "tab_x.txt").read_text(encoding="utf-8").strip()
        assert head == str(got["head_seq"])

    def test_trace_sidecar_matches_report(self) -> None:
        """Trace sidecar rows align with the JSON report for primary and profile scenarios."""
        for scenario in ("tab_x", "tab_trim"):
            expected = expected_for(scenario)
            pre_trim = get_pre_trim(scenario)
            run_driver(scenario)
            assert read_trace() == expected_trace(expected, pre_trim)

    def test_verification_scenario_matches_recompute(self) -> None:
        """Closed grading scenario matches independent recompute."""
        install_probe_scenario("tab_probe", PROBE_ROOT)
        expected = expected_for("tab_probe")
        got = run_driver("tab_probe")
        assert got == expected

    def test_verification_profile_scenario_matches_recompute(self) -> None:
        """Closed grading profile scenario matches independent recompute and trace."""
        install_probe_scenario("tab_probe_v", PROBE_ROOT)
        expected = expected_for("tab_probe_v")
        pre_trim = get_pre_trim("tab_probe_v")
        got = run_driver("tab_probe_v")
        assert got == expected
        assert read_trace() == expected_trace(expected, pre_trim)
