"""Milestone 2: trim markers, profile ordering, lane filters, and applied recounts."""

from __future__ import annotations

import pytest

from plate_common import (
    PROFILE_DIR,
    clear_outputs,
    expected_for,
    expected_trace,
    get_pre_trim,
    read_trace,
    run_driver,
)


@pytest.fixture(autouse=True)
def _clear_outputs() -> None:
    clear_outputs()


class TestMilestone2:
    def test_marker_scenario_limits_rows_and_applied(self) -> None:
        """Rollback marker scenario retains the expected rows and applied tally."""
        expected = expected_for("tab_s")
        got = run_driver("tab_s")
        assert got == expected

    def test_marker_zero_leaves_empty_retained_set(self) -> None:
        """rollback_after=0 leaves empty retained set and digest_chain empty."""
        got = run_driver("tab_w")
        assert got == expected_for("tab_w")

    def test_plate_lane_filter_before_trim(self) -> None:
        """plate_lane keeps only matching PLT5 rows before trimming and tallying."""
        expected = expected_for("tab_z")
        got = run_driver("tab_z")
        assert got == expected

    def test_dual_trim_profile_scenario_matches_recompute(self) -> None:
        """Profile-driven dual trim scenario matches independent recompute."""
        expected = expected_for("tab_trim")
        got = run_driver("tab_trim")
        assert got == expected

    def test_profile_sequence_mutation_changes_output(self) -> None:
        """Changing profile trim steps changes report and trace outputs."""
        full_expected = expected_for("tab_trim")
        pre_trim = get_pre_trim("tab_trim")
        profile_path = PROFILE_DIR / "plate_ceiling_then_floor.toml"
        original = profile_path.read_text(encoding="utf-8")
        profile_path.write_text('trim_sequence = ["rollback_after"]\n', encoding="utf-8")
        try:
            got = run_driver("tab_trim")
            assert got != full_expected
            mutated_expected = expected_for("tab_trim")
            assert got == mutated_expected
            assert read_trace() != expected_trace(full_expected, pre_trim)
        finally:
            profile_path.write_text(original, encoding="utf-8")

    def test_modulo_prune_profile_scenario_matches_recompute(self) -> None:
        """modulo_prune profile filters out segments whose seq modulo matches 0."""
        profile_path = PROFILE_DIR / "plate_ceiling_then_floor.toml"
        original = profile_path.read_text(encoding="utf-8")
        profile_path.write_text(original + "\nmodulo_prune = 3\n", encoding="utf-8")
        try:
            expected = expected_for("tab_trim")
            got = run_driver("tab_trim")
            assert got == expected
        finally:
            profile_path.write_text(original, encoding="utf-8")

    def test_profile_prune_scenario_matches_recompute(self) -> None:
        """tab_y with profile_01 prune_below trim matches independent recompute."""
        expected = expected_for("tab_y")
        got = run_driver("tab_y")
        assert got == expected

    def test_profile_lane_mask_filters_before_trim(self) -> None:
        """Profile lane_mask keeps only rows whose plate lane bit is set."""
        expected = expected_for("tab_lm")
        got = run_driver("tab_lm")
        assert got == expected
