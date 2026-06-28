"""Milestone 2 — fixed graph, cap rollback, incremental reuse proof."""

from __future__ import annotations

from trace_helpers import (
    assert_matrix_law,
    header_bump_compiles_main,
    header_bump_ring_recovered,
    run_trace,
    triple_incremental_only_reuse,
    unchanged_matches_header_bump_app_v1,
)


class TestMilestone2:
    def test_chk_m2_a0(self):
        """header_bump matrix law for both link targets."""
        doc = run_trace()
        assert_matrix_law(doc, "header_bump")

    def test_chk_m2_a1(self):
        """unchanged_control app_v1 digests match header_bump app_v1 on a fixed graph."""
        doc = run_trace()
        unchanged_matches_header_bump_app_v1(doc)

    def test_chk_m2_a2(self):
        """cap_rollback matrix law after mid-sequence bump without full wipe."""
        doc = run_trace()
        assert_matrix_law(doc, "cap_rollback")

    def test_chk_m2_a3(self):
        """Three consecutive incremental-only passes compile nothing and keep skipping."""
        triple_incremental_only_reuse()

    def test_chk_m2_a4(self):
        """Cap-bump quick path recompiles main and realigns ring generations."""
        header_bump_ring_recovered()

    def test_chk_m2_a5(self):
        """Cap-bump quick path recompiles main.c and refreshes object vs header mtimes."""
        header_bump_compiles_main()
