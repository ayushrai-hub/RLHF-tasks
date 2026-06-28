"""Milestone 3 — rerun safety, cap rollback replay, multi-run stability."""

from __future__ import annotations

from trace_helpers import (
    cap_rollback_manual_ring_stable,
    plan_cap_value,
    rows_for,
    run_trace,
    same_second_incremental_chain,
    trace_bytes_stable,
    trace_stable_after_incremental_only,
    triple_incremental_stable,
)


class TestMilestone3:
    def test_chk_m3_a0(self):
        """same_second_seq: quick equals full for every target."""
        doc = run_trace()
        for row in rows_for(doc, "same_second_seq"):
            assert row["fast_digest_hex"] == row["pristine_digest_hex"]

    def test_chk_m3_a1(self):
        """Incremental-only after trace leaves rebuild_trace.json byte-stable."""
        trace_stable_after_incremental_only()

    def test_chk_m3_a2(self):
        """cap_rollback remains stable under full trace replay."""
        doc = run_trace()
        expected = plan_cap_value("cap_rollback")
        for row in rows_for(doc, "cap_rollback"):
            assert row["fast_digest_hex"] == row["pristine_digest_hex"]
            assert row["capability_tag"] == expected

    def test_chk_m3_a3(self):
        """Cap rollback and same-second paths keep ring alignment and incremental reuse."""
        cap_rollback_manual_ring_stable()
        same_second_incremental_chain()

    def test_chk_m3_a4(self):
        """Back-to-back trace_host runs produce identical rebuild_trace.json bytes."""
        trace_bytes_stable()

    def test_chk_m3_a5(self):
        """Triple cap cycle then noop quick rebuild keeps matrix law and aligned ring."""
        triple_incremental_stable()
