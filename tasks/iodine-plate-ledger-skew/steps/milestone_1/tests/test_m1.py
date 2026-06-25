"""Milestone 1: PLT5 parsing, digest verification, and segment report ordering."""

from __future__ import annotations

import json

import pytest

from plate_common import OUT, clear_outputs, expected_for, run_driver


@pytest.fixture(autouse=True)
def _clear_outputs() -> None:
    clear_outputs()


class TestMilestone1:
    def test_primary_report_matches_independent_recompute(self) -> None:
        """Primary scenario report matches independent byte recompute."""
        expected = expected_for("tab_x")
        got = run_driver("tab_x")
        assert got == expected

    def test_primary_rebuild_is_idempotent(self) -> None:
        """Running the driver twice on the primary scenario yields the same report."""
        first = run_driver("tab_x")
        second = run_driver("tab_x")
        assert second == first

    def test_row_order_follows_sequence_field(self) -> None:
        """Segment rows appear sorted by seq, not lexical filename order."""
        expected = expected_for("tab_x")
        got = run_driver("tab_x")
        seqs = [row["seq"] for row in got["segments"]]
        expected_seqs = [row["seq"] for row in expected["segments"]]
        assert seqs == sorted(seqs)
        assert seqs == expected_seqs

    def test_lane_anchor_digest_scenario_matches_recompute(self) -> None:
        """tab_v profile digest_anchor=1 requires lane-span CRC verification."""
        expected = expected_for("tab_v")
        got = run_driver("tab_v")
        assert got == expected

    def test_chain_field_requires_all_digests(self) -> None:
        """digest_chain is valid only when every retained row passes digest check."""
        got = run_driver("tab_t")
        expected = expected_for("tab_t")
        assert got == expected

    def test_hand_written_output_is_replaced_by_driver(self) -> None:
        """A static JSON file is replaced when the driver runs."""
        OUT.parent.mkdir(parents=True, exist_ok=True)
        decoy = {
            "scenario": "tab_x",
            "head_seq": 0,
            "records_applied": 0,
            "digest_chain": "empty",
            "segments": [],
        }
        OUT.write_text(json.dumps(decoy) + "\n", encoding="utf-8")
        got = run_driver("tab_x")
        assert got != decoy
