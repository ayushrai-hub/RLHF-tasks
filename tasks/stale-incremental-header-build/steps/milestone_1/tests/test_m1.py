"""Milestone 1 — diagnose quick vs full divergence, ring staleness, journal surfaces."""

from __future__ import annotations

import json

from trace_helpers import (
    DELTA,
    GEN_HDR,
    JOURNAL_SURF,
    MAIN_OBJ,
    RING_AUDIT,
    assert_fix_frontier_unchanged,
    delta_matches_fresh_trace,
    expected_broken_plan_ids,
    expected_journal_surfaces,
    expected_quick_full_delta,
    reproduce_header_bump_cap,
    ring_covers_both_targets,
    run_trace,
)


class TestMilestone1:
    def test_chk_m1_a0(self):
        """quick_full_delta.json matches a freshly regenerated trace, not a stale copy."""
        assert DELTA.is_file(), "write /app/output/quick_full_delta.json"
        assert delta_matches_fresh_trace(DELTA)
        broken = expected_broken_plan_ids()
        assert "header_bump" in broken
        assert "unchanged_control" not in broken
        assert len(broken) >= 2

    def test_chk_m1_a1(self):
        """quick_full_delta.json lists every plan with live digest inequality."""
        assert DELTA.is_file(), "write /app/output/quick_full_delta.json"
        live_trace = run_trace()
        agent_doc = json.loads(DELTA.read_text(encoding="utf-8"))
        want = expected_quick_full_delta(live_trace)
        assert agent_doc == want

    def test_chk_m1_a2(self):
        """slot_ring_audit.json reflects stale ring generations after cap bump."""
        assert RING_AUDIT.is_file(), "write /app/output/slot_ring_audit.json"
        agent_doc = json.loads(RING_AUDIT.read_text(encoding="utf-8"))
        assert agent_doc["any_stale_gen"] is True
        assert agent_doc["entries"], "ring must record link blobs after cap bump"
        for entry in agent_doc["entries"]:
            assert entry["blob_path"].endswith(".bin")
            assert entry["gen_aligned"] == (
                entry["stored_gen"] == entry["live_gen"]
            )
            assert entry["gen_aligned"] is False

    def test_chk_m1_a3(self):
        """journal_surfaces.json shows skip on main.c after header bump reproduction."""
        assert JOURNAL_SURF.is_file(), "write /app/output/journal_surfaces.json"
        agent_doc = json.loads(JOURNAL_SURF.read_text(encoding="utf-8"))
        want = expected_journal_surfaces()
        assert agent_doc == want
        main_surface = next(
            s for s in want["surfaces"] if s["source_rel"] == "app_v1/main.c"
        )
        assert main_surface["last_action_skip"] is True

    def test_chk_m1_a4(self):
        """slot_ring_audit.json records stale generations for both link targets."""
        assert RING_AUDIT.is_file(), "write /app/output/slot_ring_audit.json"
        agent_doc = json.loads(RING_AUDIT.read_text(encoding="utf-8"))
        assert agent_doc["any_stale_gen"] is True
        assert ring_covers_both_targets(agent_doc["entries"])
        for entry in agent_doc["entries"]:
            assert entry["gen_aligned"] is False
            assert entry["stored_gen"] != entry["live_gen"]

    def test_chk_m1_a5(self):
        """Cap-bump reproduction leaves main.o older than header and frontier untouched."""
        reproduce_header_bump_cap()
        assert int(MAIN_OBJ.stat().st_mtime * 1000) < int(
            GEN_HDR.stat().st_mtime * 1000
        )
        assert_fix_frontier_unchanged()
