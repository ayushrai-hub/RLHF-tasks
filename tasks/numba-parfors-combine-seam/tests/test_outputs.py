"""Domain verifier for r8 replay trace contract."""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/app/docs")

from r8_session import (
    MIN_CHAIN_ROWS,
    MIN_WAL_LINES,
    STATE,
    WAL_TAB,
    R8ReplaySession,
    bust_before_success,
    lineage_seal_from_wal,
    load_checkpoint,
    load_epoch,
    load_report,
    load_wal,
    parse_tab,
    rows_for,
    run_chain,
    run_emit,
    run_emit_allow_fail,
    run_invoke,
    run_recover,
    scenario_include_tab,
    scenario_metrics_epoch,
    shipped_gen,
    sort_rows,
    verify_checkpoint_seals,
    verify_cross_view_policy,
    verify_digest_slot_keys,
    verify_epoch_transition_cache,
    verify_metrics_epoch,
    verify_order_seal_bust_mixing,
    verify_row_digest,
    verify_row_schema,
    verify_s0_generations,
    verify_scenarios_present,
    verify_seq_no_reset,
    verify_r8_narrow_report,
    verify_transition_rows,
    wipe_workspace,
)


def test_q00_cold_warm_parity(session: R8ReplaySession) -> None:
    """Independent cold and warm s0 replays produce identical epoch rows and digest (instruction)."""
    run_chain(session, 0, emit=True)
    cold_fp = load_report(session)["body_digest"]
    cold_epoch = load_epoch(session, 0)
    wipe_workspace(session)
    run_chain(session, 0, emit=True)
    warm = load_report(session)
    assert warm["body_digest"] == cold_fp
    assert sort_rows(cold_epoch) == sort_rows(load_epoch(session, 0))
    verify_s0_generations(session, warm)


def test_q01_beta_skew(session: R8ReplaySession) -> None:
    """Scenario s1 live rows document reduce-vs-live skew after promote reorder (instruction)."""
    run_chain(session, 1, emit=True)
    report = load_report(session)
    s1_reduce = rows_for(session, report, 1, "reduce")[0]
    s1_live = rows_for(session, report, 1, "live")[0]
    assert s1_reduce["generation"] >= shipped_gen(1)
    assert s1_reduce["generation"] == s1_live["generation"]
    live_rows = rows_for(session, report, 1, "live")
    assert len(live_rows) >= 2
    assert any(r.get("action_code") == 5 for r in live_rows)
    assert all(int(r.get("action_code", 0)) != 7 for r in live_rows)
    verify_digest_slot_keys()
    verify_metrics_epoch(scenario_metrics_epoch(1))


def test_q02_gamma_gap(session: R8ReplaySession) -> None:
    """Cross-promote skew surfaces non-zero action rows when live generation exceeds store generation (instruction)."""
    run_chain(session, 2, emit=True)
    report = load_report(session)
    for n in (1, 2):
        live_rows = rows_for(session, report, n, "live")
        promote_gen = max(r["generation"] for r in rows_for(session, report, n, "promote"))
        for row in live_rows:
            if int(row["generation"]) > promote_gen:
                assert int(row.get("action_code", 0)) != 0
    s2_live = rows_for(session, report, 2, "live")
    assert len(s2_live) >= 2
    assert any(int(r.get("action_code", 0)) != 0 for r in s2_live[1:])


def test_q03_delta_bust(session: R8ReplaySession) -> None:
    """Scenarios after baseline log bust before success; s1 reduce gen meets shipped profile (instruction, r8_contract.md Phase order)."""
    run_chain(session, 1)
    bust_before_success(load_wal(session), 1)
    epoch_rows = load_epoch(session, 1)
    reduce_rows = [r for r in epoch_rows if r.get("scenario") == 1 and r.get("view") == "reduce"]
    assert reduce_rows[0]["generation"] >= shipped_gen(1)
    verify_digest_slot_keys()


def test_q04_chain_monotone(session: R8ReplaySession) -> None:
    """Append-log seq increases monotonically across s0 through s4 with bust-before-success per scenario (instruction, r8_contract.md WAL sequence discipline)."""
    run_chain(session, 4)
    records = load_wal(session)
    seqs = [int(rec["seq"]) for rec in records]
    assert len(seqs) >= MIN_WAL_LINES
    for prev, cur in zip(seqs, seqs[1:]):
        assert cur > prev
    for scenario in range(1, 5):
        bust_before_success(records, scenario)


def test_q05_hash_parity(session: R8ReplaySession) -> None:
    """Full s0 through s4 integration: schema, digest, cross-view policy, transitions, checkpoint seals (instruction, r8_contract.md)."""
    run_chain(session, 4, emit=True)
    report = load_report(session)
    verify_row_schema(report)
    verify_row_digest(report)
    verify_s0_generations(session, report)
    verify_scenarios_present(session, report, 4)
    verify_cross_view_policy(session, report)
    verify_transition_rows(session, report)
    assert len(report["epochs"]) >= MIN_CHAIN_ROWS
    verify_checkpoint_seals(session)
    verify_metrics_epoch(scenario_metrics_epoch(4))


def test_q06_repeat_stable(session: R8ReplaySession) -> None:
    """Checkpoint seals match append-log recomputation; body_digest stable across repeat emit (instruction, r8_contract.md Idempotency)."""
    run_chain(session, 4)
    verify_checkpoint_seals(session)
    run_emit(session)
    first = load_report(session)["body_digest"]
    assert lineage_seal_from_wal(load_wal(session)) > 0
    run_emit(session)
    assert load_report(session)["body_digest"] == first


def test_q07_s0_survives(session: R8ReplaySession) -> None:
    """Checkpoint poison plus rebuild restores seals and preserves s0 baseline through s3 (instruction)."""
    run_chain(session, 2)
    cp = load_checkpoint(session)
    cp["lineage_seal"] = 0
    (STATE / "checkpoint.json").write_text(json.dumps(cp) + "\n", encoding="utf-8")
    assert run_recover(session) == 0
    run_invoke(session, 3)
    run_emit(session)
    verify_s0_generations(session, load_report(session))
    verify_checkpoint_seals(session)


def test_q08_step_chain(session: R8ReplaySession) -> None:
    """Repeated single-scenario replay yields identical stored rows when step order is stable (instruction)."""
    run_chain(session, 0)
    run_invoke(session, 1)
    first = load_epoch(session, 1)
    seal_a = lineage_seal_from_wal(load_wal(session))
    run_invoke(session, 1)
    second = load_epoch(session, 1)
    assert sort_rows(first) == sort_rows(second)
    assert lineage_seal_from_wal(load_wal(session)) >= seal_a
    verify_epoch_transition_cache(session, 1)
    bust_before_success(load_wal(session), 1)


def test_q09_denied_case(session: R8ReplaySession) -> None:
    """Scenario s3 reflects denied freshness generation with live deny outcomes (instruction)."""
    run_chain(session, 3, emit=True)
    report = load_report(session)
    live_rows = rows_for(session, report, 3, "live")
    assert len(live_rows) >= 2
    assert any(r.get("action_code") == 9 for r in live_rows)
    frag_epoch, digest = parse_tab(scenario_include_tab(3))
    assert digest
    verify_metrics_epoch(frag_epoch)
    promote_rows = rows_for(session, report, 3, "promote")
    assert max(r["generation"] for r in promote_rows) >= shipped_gen(3)


def test_q10_abs_shift(session: R8ReplaySession) -> None:
    """Deny tranche s3 sync records live_gen above feed_gen after write bumps (instruction, r8_contract.md Scenario s3)."""
    run_chain(session, 3, emit=True)
    records = load_wal(session)
    sync_records = [r for r in records if int(r["scenario"]) == 3 and r["phase"] == "sync"]
    tail = sync_records[-1]
    feed = int(tail["feed_gen"])
    live = int(tail["live_gen"])
    assert live > feed
    assert live - feed >= 2
    report = load_report(session)
    reduce = rows_for(session, report, 3, "reduce")[0]
    assert reduce["generation"] >= shipped_gen(3)
    assert len(rows_for(session, report, 3, "live")) >= 2


def test_q11_double_rebuild_stable(session: R8ReplaySession) -> None:
    """Rebuild refuses when checkpoint seal disagrees with append log (instruction)."""
    run_chain(session, 3)
    cp = load_checkpoint(session)
    cp["lineage_seal"] = 0
    (STATE / "checkpoint.json").write_text(json.dumps(cp) + "\n", encoding="utf-8")
    assert run_emit_allow_fail(session) != 0
    assert run_recover(session) == 0
    verify_checkpoint_seals(session)
    run_emit(session)
    assert load_report(session)["epochs"]


def test_q12_partial_seal_rejected(session: R8ReplaySession) -> None:
    """Digest changes only after scenario s4 completes the delayed readopt chain (instruction)."""
    run_chain(session, 3, emit=True)
    before = load_report(session)
    assert all(r["scenario"] <= 3 for r in before["epochs"])
    fp_before = before["body_digest"]
    run_invoke(session, 4)
    run_emit(session)
    after = load_report(session)
    assert any(r["scenario"] == 4 for r in after["epochs"])
    assert after["body_digest"] != fp_before
    verify_transition_rows(session, after)


def test_q13_delayed_shift(session: R8ReplaySession) -> None:
    """Report tool refuses when any append log line carries an invalid CRC (r8_contract.md)."""
    run_chain(session, 2)
    wal_path = STATE / "wal" / "chain.wal"
    lines = wal_path.read_text(encoding="utf-8").splitlines()
    body, _crc = lines[-1].split(WAL_TAB, 1)
    lines[-1] = f"{body}\t0"
    wal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cp = load_checkpoint(session)
    cp["valid"] = True
    (STATE / "checkpoint.json").write_text(json.dumps(cp) + "\n", encoding="utf-8")
    assert run_emit_allow_fail(session) != 0


def test_q14_corrupt_crc_rejected(session: R8ReplaySession) -> None:
    """Scenario s4 documents readopt success after deny when full chain is replayed (instruction)."""
    run_chain(session, 4, emit=True)
    report = load_report(session)
    live_rows = rows_for(session, report, 4, "live")
    assert len(live_rows) >= 2
    assert any(r.get("action_code") == 6 for r in live_rows)
    reduce_row = rows_for(session, report, 4, "reduce")[0]
    live_row = rows_for(session, report, 4, "live")[0]
    assert reduce_row["generation"] == live_row["generation"]
    verify_metrics_epoch(scenario_metrics_epoch(4))


def test_q15_s4_late_wrap(session: R8ReplaySession) -> None:
    """Append-log seq never resets at scenario boundaries (instruction, r8_contract.md WAL sequence discipline)."""
    run_chain(session, 4)
    verify_seq_no_reset(load_wal(session))


def test_q16_cross_scope_monotone(session: R8ReplaySession) -> None:
    """Order seal uses bust-then-success mixing distinct from broken success-only path (instruction, r8_contract.md Order seal bust mixing)."""
    run_chain(session, 1)
    records = load_wal(session)
    verify_order_seal_bust_mixing(records)
    verify_checkpoint_seals(session)


def test_q17_seal_beef_term(session: R8ReplaySession) -> None:
    """s1 final sync-phase append record captures aligned feed_gen and live_gen (instruction, r8_contract.md Sync-phase WAL capture)."""
    run_chain(session, 1)
    sync_records = [r for r in load_wal(session) if int(r["scenario"]) == 1 and r["phase"] == "sync"]
    tail = sync_records[-1]
    assert int(tail["feed_gen"]) == int(tail["live_gen"])


def test_q18_sync_gen_alignment(session: R8ReplaySession) -> None:
    """Third consecutive s1 replay leaves epoch cache rows unchanged (instruction)."""
    run_chain(session, 0)
    for _ in range(3):
        run_invoke(session, 1)
    rows = load_epoch(session, 1)
    run_invoke(session, 1)
    again = load_epoch(session, 1)
    assert sort_rows(rows) == sort_rows(again)
    run_chain(session, 2, emit=True)
    report = load_report(session)
    verify_r8_narrow_report(session, report, through_scenario=2)


