#!/usr/bin/env python3
"""Verifier for k7 cross-view authority report."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import zlib
from pathlib import Path

import pytest

INVOKE = "/app/environment/tools/k7_invoke"
Z2 = "/app/environment/tools/k7_z2"
RECOVER = "/app/environment/tools/k7_recover"
OUT = Path("/app/output/k7_trace.json")
SEQ_ROOT = Path("/app/cases/seq")
HIDDEN = Path("/tests/hidden")
FIXTURE_MANIFEST = HIDDEN / "fixture_manifest.sha256"
STATE = Path("/app/replay-state")
STORE = STATE / "store"
WRITE_GEN_DELTA = 1
WAL_SEP = "\t"
VIEWS = ("spool", "drift", "live")
RUN_TIMEOUT = 300
# Documented in environment/docs/k7_contract.md (Harness thresholds).
MIN_FULL_CHAIN_ROWS = 18
MIN_WAL_RECORDS_S04 = 25


@pytest.fixture(scope="session", autouse=True)
def _verify_hidden_fixture_manifest() -> None:
    """Anti-cheat: verifier-only overlays must match pinned digests."""
    assert FIXTURE_MANIFEST.is_file(), "missing hidden fixture manifest"
    for line in FIXTURE_MANIFEST.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, rel = line.split(maxsplit=1)
        path = HIDDEN / rel
        assert path.is_file(), f"missing hidden fixture {rel}"
        payload = path.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == digest


@pytest.fixture(scope="session", autouse=True)
def _rebuild_tools_from_source() -> None:
    """Rebuild replay binaries from agent-edited sources before grading."""
    subprocess.run(
        ["cargo", "build", "--release", "--locked"],
        cwd="/app/environment",
        check=True,
        timeout=900,
        env=os.environ,
    )


def _wal_crc(payload: str) -> int:
    return zlib.crc32(payload.encode("utf-8")) & 0xFFFFFFFF


def _row_lines(rows: list[dict]) -> list[str]:
    return [
        f"{r['scenario']},{r['view']},{r['principal']},{r['label']},{r['generation']}"
        for r in rows
    ]


def _fingerprint_generation_order(lines: list[str]) -> str:
    ordered = sorted(lines, key=lambda line: line.rsplit(",", 1)[-1])
    return hashlib.sha256("\n".join(ordered).encode("utf-8")).hexdigest()


def _lines_differ_lex_vs_generation(lines: list[str]) -> bool:
    return sorted(lines, key=lambda line: line.rsplit(",", 1)[-1]) != sorted(lines)


def _fingerprint(rows: list[dict]) -> str:
    parts = [
        f"{r['scenario']},{r['view']},{r['principal']},{r['label']},{r['generation']}"
        for r in rows
    ]
    parts.sort()
    payload = "\n".join(parts) + "\n"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _compute_order_seal(chain: list[dict]) -> int:
    """Mirror environment/src/wal.rs compute_order_seal for harness checks."""
    seal = 0
    last_scenario = 0xFFFFFFFF
    saw_bust = False
    for rec in chain:
        sc = int(rec["scenario"])
        if sc != last_scenario:
            last_scenario = sc
            saw_bust = False
        phase = rec["phase"]
        if phase == "bust":
            saw_bust = True
        if phase == "success" and saw_bust:
            seal = (seal + 0xBEEF) & 0xFFFFFFFFFFFFFFFF
        if phase == "success" and not saw_bust:
            seal = ((seal * 31) + int(rec["seq"])) & 0xFFFFFFFFFFFFFFFF
        if phase == "bust" and not saw_bust:
            seal = ((seal * 37) + int(rec["seq"])) & 0xFFFFFFFFFFFFFFFF
    return seal


def _parse_tree(path: Path) -> dict[str, dict[str, int | str]]:
    slots: dict[str, dict[str, int | str]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = dict(item.split("=", 1) for item in line.split())
        name = (parts.pop("ward", "") or parts.pop("spool", "")).strip()
        if not name:
            continue
        slots[name] = dict(
            principal=parts.get("principal", "svc1"),
            label=parts.get("label", "ROOT"),
            gen=int(parts["gen"]),
            action=int(parts.get("action", 0)),
        )
    return slots


def _parse_frag(path: Path) -> tuple[int, str]:
    epoch = 1
    digest = ""
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        for item in line.split():
            if "=" in item:
                k, v = item.split("=", 1)
                if k == "epoch":
                    epoch = int(v)
                elif k == "digest":
                    digest = v
    return epoch, digest


def _renew_baseline_gen(scenario: int) -> int:
    return int(_parse_tree(SEQ_ROOT / f"s{scenario}/a0.tree")["active"]["gen"]) + WRITE_GEN_DELTA


def _apply_hidden_overlay(scenario: int, leaf: str = "i0.frag") -> None:
    hidden = HIDDEN / "seq" / f"s{scenario}" / leaf
    target = SEQ_ROOT / f"s{scenario}" / leaf
    shutil.copy(hidden, target)


def _reset_workspace() -> None:
    if OUT.exists():
        OUT.unlink()
    if STATE.exists():
        shutil.rmtree(STATE)
    STATE.mkdir(parents=True, exist_ok=True)
    for sub in ("store", "live", "drift", "wal"):
        (STATE / sub).mkdir(exist_ok=True)


def _replay_scenario(scenario: int) -> None:
    subprocess.run(
        [INVOKE, "--scenario", str(scenario)],
        check=True,
        timeout=RUN_TIMEOUT,
    )
    cache = STATE / f"epoch_{scenario}.json"
    assert len(json.loads(cache.read_text(encoding="utf-8"))) >= 1


def _replay_range(start: int, end: int) -> None:
    for n in range(start, end + 1):
        _replay_scenario(n)


def _emit_report() -> None:
    subprocess.run(
        [Z2, "--out", "/app/output/k7_trace.json"],
        check=True,
        timeout=RUN_TIMEOUT,
    )


def _replay_through(scenario: int, *, emit: bool = False) -> None:
    _reset_workspace()
    _replay_range(0, scenario)
    if emit:
        _emit_report()


def _read_wal_records() -> list[dict]:
    wal_path = STATE / "wal" / "chain.wal"
    records: list[dict] = []
    for line in wal_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        body, crc_str = line.split(WAL_SEP, 1)
        rec = json.loads(body)
        payload = (
            f"{rec['scenario']}:{rec['phase']}:{rec['ward_gen']}:"
            f"{rec['frame_gen']}:{rec['seq']}"
        )
        assert int(crc_str) == _wal_crc(payload)
        records.append(rec)
    return records


def _load_report() -> dict:
    return json.loads(OUT.read_text(encoding="utf-8"))


def _rows_for(report: dict, scenario: int, view: str) -> list[dict]:
    return [r for r in report["rows"] if r["scenario"] == scenario and r["view"] == view]


def _active_row(rows: list[dict]) -> dict:
    assert len(rows) >= 1
    return rows[0]


def _sorted_rows(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda r: (r["scenario"], r["view"], r["principal"], r["label"], r["generation"]),
    )


def _phases_for_scenario(records: list[dict], scenario: int) -> list[str]:
    return [rec["phase"] for rec in records if rec["scenario"] == scenario]


def _assert_bust_before_success(records: list[dict], scenario: int) -> None:
    phases = _phases_for_scenario(records, scenario)
    if scenario == 0 or not phases:
        return
    assert phases[0] == "bust"
    assert "success" in phases
    assert phases.index("success") > phases.index("bust")


def _assert_row_schema(report: dict) -> None:
    assert "rows" in report
    assert "chain_fingerprint" in report
    for row in report["rows"]:
        for key in ("scenario", "view", "principal", "label", "generation", "action_code"):
            assert key in row
        assert row["view"] in VIEWS


def _assert_fingerprint_self_consistent(report: dict) -> None:
    assert report["chain_fingerprint"] == _fingerprint(report["rows"])


def _assert_s0_baseline_rows(report: dict) -> None:
    expected = _renew_baseline_gen(0)
    for view in VIEWS:
        row = _active_row(_rows_for(report, 0, view))
        assert row["generation"] == expected


def _assert_scenarios_covered(report: dict, max_scenario: int) -> None:
    for n in range(max_scenario + 1):
        for view in VIEWS:
            assert len(_rows_for(report, n, view)) >= 1


def _assert_cross_view_invariants(report: dict, max_scenario: int = 4) -> None:
    for n in range(1, max_scenario + 1):
        seg_rows = _rows_for(report, n, "spool")
        live_rows = _rows_for(report, n, "live")
        rld_rows = _rows_for(report, n, "drift")
        assert seg_rows and live_rows and rld_rows
        seg = _active_row(seg_rows)
        live = _active_row(live_rows)
        if n == 3 and any(r.get("action_code") == 9 for r in live_rows):
            continue
        assert seg["generation"] == live["generation"]
        rld_gen = max(r["generation"] for r in rld_rows)
        if live["generation"] > rld_gen:
            assert any(r.get("action_code", 0) != 0 for r in live_rows)


def _assert_transition_contract(report: dict) -> None:
    assert len(_rows_for(report, 2, "live")) >= 2
    assert len(_rows_for(report, 3, "live")) >= 2
    assert len(_rows_for(report, 4, "live")) >= 2
    assert any(r.get("action_code") == 9 for r in _rows_for(report, 3, "live"))
    assert any(r.get("action_code") == 6 for r in _rows_for(report, 4, "live"))
    s2_live = _rows_for(report, 2, "live")
    assert any(r.get("action_code", 0) != 0 for r in s2_live[1:])


def _assert_checkpoint_seal_matches_wal() -> None:
    records = _read_wal_records()
    cp = json.loads((STATE / "checkpoint.json").read_text(encoding="utf-8"))
    assert cp.get("valid") is True
    assert cp.get("order_seal") == _compute_order_seal(records)
    assert int(cp.get("order_seal", -1)) == _compute_order_seal(records)


def _assert_epoch_has_transition_rows(scenario: int) -> None:
    rows = json.loads((STATE / f"epoch_{scenario}.json").read_text(encoding="utf-8"))
    live_rows = [r for r in rows if r.get("view") == "live"]
    assert len(live_rows) >= 2
    assert any(int(r.get("action_code", 0)) != 0 for r in live_rows)


def _assert_store_lineage_keys() -> None:
    """Digest-bearing slot keys must appear after replay (not serial-only basenames)."""
    slot_files = list(STORE.glob("*.ward"))
    assert slot_files
    joined = " ".join(p.name for p in slot_files)
    _, digest = _parse_frag(SEQ_ROOT / "s1/i0.frag")
    assert digest
    assert digest in joined


def _assert_metrics_leaf_epoch(min_epoch: int) -> None:
    metrics_path = STATE / "last_metrics.json"
    assert metrics_path.is_file()
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    assert int(metrics.get("leaf_epoch", 0)) >= min_epoch


def _compute_order_seal_alt(chain: list[dict]) -> int:
    """Broken seal mixing: bust-success pairs use multiply instead of 0xBEEF."""
    seal = 0
    last_scenario = 0xFFFFFFFF
    saw_bust = False
    for rec in chain:
        sc = int(rec["scenario"])
        if sc != last_scenario:
            last_scenario = sc
            saw_bust = False
        phase = rec["phase"]
        if phase == "bust":
            saw_bust = True
        if phase == "success" and saw_bust:
            seal = ((seal * 31) + int(rec["seq"])) & 0xFFFFFFFFFFFFFFFF
        if phase == "success" and not saw_bust:
            seal = ((seal * 31) + int(rec["seq"])) & 0xFFFFFFFFFFFFFFFF
        if phase == "bust" and not saw_bust:
            seal = ((seal * 37) + int(rec["seq"])) & 0xFFFFFFFFFFFFFFFF
    return seal


def _assert_epoch_seg_live_parity(scenario: int) -> None:
    rows = json.loads((STATE / f"epoch_{scenario}.json").read_text(encoding="utf-8"))
    seg_rows = [r for r in rows if r.get("view") == "spool"]
    live_active = [
        r
        for r in rows
        if r.get("view") == "live" and int(r.get("action_code", 0)) == 0
    ]
    if scenario < 1 or not seg_rows or not live_active:
        return
    seg = _active_row(seg_rows)
    live = _active_row(live_active)
    if scenario == 3 and any(int(r.get("action_code", 0)) == 9 for r in rows if r.get("view") == "live"):
        return
    assert seg["generation"] == live["generation"]


def _assert_wal_seq_cross_scenario(records: list[dict]) -> None:
    by_scenario: dict[int, list[int]] = {}
    for rec in records:
        by_scenario.setdefault(int(rec["scenario"]), []).append(int(rec["seq"]))
    for scenario in range(2, 5):
        if scenario not in by_scenario or scenario - 1 not in by_scenario:
            continue
        assert min(by_scenario[scenario]) > max(by_scenario[scenario - 1])


def _lineage_feed_only_seal(chain: list[dict]) -> int:
    """Broken lineage: fold ward_gen into live component slot."""
    sync_tail: dict[int, dict] = {}
    for rec in chain:
        if rec["phase"] == "sync":
            sync_tail[int(rec["scenario"])] = rec
    seal = 0
    for scenario in sorted(sync_tail):
        rec = sync_tail[scenario]
        live_component = int(rec["ward_gen"])
        seal = (
            (seal * 131)
            + (scenario << 24)
            + (int(rec["ward_gen"]) << 12)
            + live_component
        ) & 0xFFFFFFFFFFFFFFFF
    return seal


def test_k00_cold_warm_parity() -> None:
    """Independent cold and warm s0 replays produce identical epoch rows and fingerprint."""
    _replay_through(0, emit=True)
    cold = _load_report()
    cold_fp = cold["chain_fingerprint"]
    cold_epoch = json.loads((STATE / "epoch_0.json").read_text(encoding="utf-8"))
    _reset_workspace()
    _replay_through(0, emit=True)
    warm = _load_report()
    assert warm["chain_fingerprint"] == cold_fp
    warm_epoch = json.loads((STATE / "epoch_0.json").read_text(encoding="utf-8"))
    assert _sorted_rows(cold_epoch) == _sorted_rows(warm_epoch)
    _assert_s0_baseline_rows(warm)


def test_k01_beta_skew() -> None:
    """Scenario s1 live rows document seg-vs-live skew after reload while first tranche enforcement rows succeeded."""
    _replay_through(1, emit=True)
    report = _load_report()
    s1_seg = _active_row(_rows_for(report, 1, "spool"))
    s1_live = _active_row(_rows_for(report, 1, "live"))
    assert s1_seg["generation"] >= _renew_baseline_gen(1)
    assert s1_seg["generation"] == s1_live["generation"]
    s1_live_rows = _rows_for(report, 1, "live")
    assert s1_live_rows
    assert not any(r.get("action_code") == 7 for r in s1_live_rows)
    _assert_store_lineage_keys()
    s1_epoch, _ = _parse_frag(SEQ_ROOT / "s1/i0.frag")
    _assert_metrics_leaf_epoch(s1_epoch)


def test_k02_cross_lane_skew() -> None:
    """When live generation exceeds rld at verify, mirror lane notes yield non-zero rld action rows."""
    _replay_through(2, emit=True)
    report = _load_report()
    for n in (1, 2):
        live = _active_row(_rows_for(report, n, "live"))
        rld_rows = _rows_for(report, n, "drift")
        assert rld_rows
        rld_gen = max(r["generation"] for r in rld_rows)
        if live["generation"] > rld_gen:
            assert any(int(r.get("action_code", 0)) != 0 for r in rld_rows)


def test_k03_delta_bust() -> None:
    """Policy generation change busts reload store entries before success reporting."""
    _replay_through(1)
    records = _read_wal_records()
    _assert_bust_before_success(records, 1)
    epoch_rows = json.loads((STATE / "epoch_1.json").read_text(encoding="utf-8"))
    seg_rows = [r for r in epoch_rows if r.get("scenario") == 1 and r.get("view") == "spool"]
    seg = _active_row(seg_rows)
    assert seg["generation"] >= _renew_baseline_gen(1)
    _assert_store_lineage_keys()


def test_k04_chain_monotone() -> None:
    """Append log seq values strictly increase across the full s0 through s4 chain."""
    _replay_through(4)
    records = _read_wal_records()
    seqs = [int(rec["seq"]) for rec in records]
    assert len(seqs) >= MIN_WAL_RECORDS_S04
    for prev, cur in zip(seqs, seqs[1:]):
        assert cur > prev
    for scenario in range(1, 5):
        _assert_bust_before_success(records, scenario)


def test_k05_hash_parity() -> None:
    """Full row set and chain_fingerprint match fixture-grounded canonical expectations for s0 through s4."""
    _replay_through(4, emit=True)
    report = _load_report()
    _assert_row_schema(report)
    _assert_fingerprint_self_consistent(report)
    _assert_s0_baseline_rows(report)
    _assert_scenarios_covered(report, 4)
    _assert_cross_view_invariants(report)
    _assert_transition_contract(report)
    assert len(report["rows"]) >= MIN_FULL_CHAIN_ROWS
    _assert_checkpoint_seal_matches_wal()
    s4_epoch, _ = _parse_frag(SEQ_ROOT / "s4/i0.frag")
    _assert_metrics_leaf_epoch(s4_epoch)


def test_k06_repeat_stable() -> None:
    """Checkpoint order_seal equals append-log recomputation; emit fingerprint stable across repeats."""
    _replay_through(4)
    _assert_checkpoint_seal_matches_wal()
    _emit_report()
    first = _load_report()["chain_fingerprint"]
    records = _read_wal_records()
    assert _compute_order_seal(records) > 0
    _emit_report()
    assert _load_report()["chain_fingerprint"] == first


def test_k07_rebuild_preserves_baseline() -> None:
    """Recover after checkpoint poison restores seals and preserves s0 baseline through s3 emit."""
    _replay_through(2)
    cp = json.loads((STATE / "checkpoint.json").read_text(encoding="utf-8"))
    cp["order_seal"] = 0
    (STATE / "checkpoint.json").write_text(json.dumps(cp) + "\n", encoding="utf-8")
    assert subprocess.run([RECOVER], check=False, timeout=RUN_TIMEOUT).returncode == 0
    _replay_scenario(3)
    _emit_report()
    report = _load_report()
    _assert_s0_baseline_rows(report)
    _assert_checkpoint_seal_matches_wal()


def test_k08_step_order() -> None:
    """Repeated single-scenario replay yields identical stored rows when step order is stable; append log records bust-before-success."""
    _replay_through(0)
    _replay_scenario(1)
    first = json.loads((STATE / "epoch_1.json").read_text(encoding="utf-8"))
    seal_a = _compute_order_seal(_read_wal_records())
    _replay_scenario(1)
    second = json.loads((STATE / "epoch_1.json").read_text(encoding="utf-8"))
    assert _sorted_rows(first) == _sorted_rows(second)
    seal_b = _compute_order_seal(_read_wal_records())
    assert seal_b >= seal_a
    _assert_bust_before_success(_read_wal_records(), 1)


def test_k09_revoke_case() -> None:
    """Scenario s3 reflects denied policy epoch with live deny outcomes."""
    _replay_through(3, emit=True)
    report = _load_report()
    live_rows = _rows_for(report, 3, "live")
    assert len(live_rows) >= 2
    assert any(r.get("action_code") == 9 for r in live_rows)
    frag_epoch, digest = _parse_frag(SEQ_ROOT / "s3/i0.frag")
    assert digest
    _assert_metrics_leaf_epoch(frag_epoch)
    rld_rows = _rows_for(report, 3, "drift")
    assert rld_rows
    assert max(r["generation"] for r in rld_rows) >= _renew_baseline_gen(3)


def test_k10_tranche_bind_shift() -> None:
    """Write phase must bump live generation on deny tranche scenarios, preserving tree skew."""
    _replay_through(3, emit=True)
    records = _read_wal_records()
    sync_records = [r for r in records if int(r["scenario"]) == 3 and r["phase"] == "sync"]
    assert sync_records
    tail = sync_records[-1]
    ward_gen = int(tail["ward_gen"])
    frame_gen = int(tail["frame_gen"])
    assert frame_gen - ward_gen == 2
    report = _load_report()
    seg = _active_row(_rows_for(report, 3, "spool"))
    assert seg["generation"] >= _renew_baseline_gen(3)
    assert len(_rows_for(report, 3, "live")) >= 2


def test_k11_double_rebuild_stable() -> None:
    """Two rebuild passes leave seal and fingerprint unchanged."""
    _replay_through(3)
    cp = json.loads((STATE / "checkpoint.json").read_text(encoding="utf-8"))
    cp["order_seal"] = 0
    (STATE / "checkpoint.json").write_text(json.dumps(cp) + "\n", encoding="utf-8")
    bad = subprocess.run(
        [Z2, "--out", "/app/output/k7_trace.json"],
        check=False,
        timeout=RUN_TIMEOUT,
    )
    assert bad.returncode != 0
    assert subprocess.run([RECOVER], check=False, timeout=RUN_TIMEOUT).returncode == 0
    _assert_checkpoint_seal_matches_wal()
    _emit_report()
    assert _load_report()["rows"]


def test_k12_partial_seal_rejected() -> None:
    """Report tool refuses when append log records transition success before reload bust for active mount."""
    _replay_through(2)
    wal_path = STATE / "wal" / "chain.wal"
    lines = [ln for ln in wal_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    records: list[dict] = []
    for line in lines:
        body, _crc = line.split(WAL_SEP, 1)
        records.append(json.loads(body))
    s1_idx = [i for i, rec in enumerate(records) if rec["scenario"] == 1]
    assert len(s1_idx) >= 2
    first, second = s1_idx[0], s1_idx[1]
    records[first]["phase"], records[second]["phase"] = (
        records[second]["phase"],
        records[first]["phase"],
    )
    patched: list[str] = []
    for rec in records:
        payload = (
            f"{rec['scenario']}:{rec['phase']}:{rec['ward_gen']}:"
            f"{rec['frame_gen']}:{rec['seq']}"
        )
        crc = str(_wal_crc(payload))
        patched.append(f"{json.dumps(rec, separators=(',', ':'))}\t{crc}")
    wal_path.write_text("\n".join(patched) + "\n", encoding="utf-8")
    cp = json.loads((STATE / "checkpoint.json").read_text(encoding="utf-8"))
    cp["valid"] = True
    (STATE / "checkpoint.json").write_text(json.dumps(cp) + "\n", encoding="utf-8")
    bad = subprocess.run(
        [Z2, "--out", "/app/output/k7_trace.json"],
        check=False,
        timeout=RUN_TIMEOUT,
    )
    assert bad.returncode != 0


def test_k13_delayed_shift() -> None:
    """Fingerprint changes only after scenario s4 completes the delayed readopt chain."""
    _replay_through(3, emit=True)
    before = _load_report()
    assert all(r["scenario"] <= 3 for r in before["rows"])
    fp_before = before["chain_fingerprint"]
    _replay_scenario(4)
    _emit_report()
    after = _load_report()
    assert any(r["scenario"] == 4 for r in after["rows"])
    assert after["chain_fingerprint"] != fp_before
    _assert_transition_contract(after)


def test_k14_corrupt_crc_rejected() -> None:
    """Emit refuses when any append log line carries an invalid CRC even if checkpoint valid is forced."""
    _replay_through(2)
    wal_path = STATE / "wal" / "chain.wal"
    lines = wal_path.read_text(encoding="utf-8").splitlines()
    body, _crc = lines[-1].split(WAL_SEP, 1)
    lines[-1] = f"{body}\t0"
    wal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cp = json.loads((STATE / "checkpoint.json").read_text(encoding="utf-8"))
    cp["valid"] = True
    (STATE / "checkpoint.json").write_text(json.dumps(cp) + "\n", encoding="utf-8")
    bad = subprocess.run(
        [Z2, "--out", "/app/output/k7_trace.json"],
        check=False,
        timeout=RUN_TIMEOUT,
    )
    assert bad.returncode != 0


def test_k15_s4_late_wrap() -> None:
    """Scenario s4 documents readopt success after deny when full chain is replayed."""
    _replay_through(4, emit=True)
    report = _load_report()
    live_rows = _rows_for(report, 4, "live")
    assert len(live_rows) >= 2
    assert any(r.get("action_code") == 6 for r in live_rows)
    seg_row = _active_row(_rows_for(report, 4, "spool"))
    live_row = _active_row(_rows_for(report, 4, "live"))
    assert seg_row["generation"] == live_row["generation"]
    s4_epoch, _ = _parse_frag(SEQ_ROOT / "s4/i0.frag")
    _assert_metrics_leaf_epoch(s4_epoch)


def test_k16_cross_scope_monotone() -> None:
    """Append-log seq must not reset at scenario boundaries."""
    _replay_through(4)
    records = _read_wal_records()
    _assert_wal_seq_cross_scenario(records)


def test_k17_order_seal_beef_term() -> None:
    """Checkpoint seal must use 0xBEEF mixing for bust-then-success pairs."""
    _replay_through(4)
    records = _read_wal_records()
    seal = _compute_order_seal(records)
    alt = _compute_order_seal_alt(records)
    assert seal != alt
    _assert_checkpoint_seal_matches_wal()


def test_k18_sync_gen_alignment() -> None:
    """Emitted spool and live generations align on hot scenarios after replay."""
    _replay_through(2, emit=True)
    report = _load_report()
    for n in (1, 2):
        spool = _active_row(_rows_for(report, n, "spool"))
        live = _active_row(_rows_for(report, n, "live"))
        assert spool["generation"] == live["generation"]


def test_k20_checkpoint_tail_align() -> None:
    """Checkpoint stores wal_seq, order_seal, and order_seal from the append log."""
    _replay_through(4)
    records = _read_wal_records()
    cp = json.loads((STATE / "checkpoint.json").read_text(encoding="utf-8"))
    tail = records[len(records) - 1]
    assert int(cp["wal_seq"]) == int(tail["seq"])
    assert int(cp["order_seal"]) == _compute_order_seal(records)
    assert int(cp["order_seal"]) == _compute_order_seal(records)


def test_k23_stale_seal_checkpoint_rejected() -> None:
    """Emit refuses when order_seal drifts from sync-phase WAL recomputation."""
    _replay_through(2)
    records = _read_wal_records()
    cp = json.loads((STATE / "checkpoint.json").read_text(encoding="utf-8"))
    cp["order_seal"] = _compute_order_seal(records) + 1
    cp["valid"] = True
    (STATE / "checkpoint.json").write_text(json.dumps(cp) + "\n", encoding="utf-8")
    bad = subprocess.run(
        [Z2, "--out", "/app/output/k7_trace.json"],
        check=False,
        timeout=RUN_TIMEOUT,
    )
    assert bad.returncode != 0


def test_k19_triple_repeat_s1_stable() -> None:
    """Third consecutive s1 replay leaves epoch cache rows unchanged."""
    _replay_through(0)
    for _ in range(3):
        _replay_scenario(1)
    rows = json.loads((STATE / "epoch_1.json").read_text(encoding="utf-8"))
    assert len(rows) >= 2
    _replay_scenario(1)
    again = json.loads((STATE / "epoch_1.json").read_text(encoding="utf-8"))
    assert _sorted_rows(rows) == _sorted_rows(again)


def test_k21_transition_rows_preserved() -> None:
    """Epoch caches retain live transition rows required for emit fold."""
    _replay_through(4)
    for scenario in (1, 2, 3, 4):
        if scenario >= 2:
            _assert_epoch_has_transition_rows(scenario)
    _emit_report()
    report = _load_report()
    _assert_transition_contract(report)
    assert len(report["rows"]) >= MIN_FULL_CHAIN_ROWS


def test_k24_truncated_log_rejected() -> None:
    """Emit refuses when checkpoint wal_seq exceeds intact append-log records."""
    _replay_through(2)
    wal_path = STATE / "wal" / "chain.wal"
    lines = wal_path.read_text(encoding="utf-8").splitlines()
    wal_path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    cp = json.loads((STATE / "checkpoint.json").read_text(encoding="utf-8"))
    cp["valid"] = True
    (STATE / "checkpoint.json").write_text(json.dumps(cp) + "\n", encoding="utf-8")
    bad = subprocess.run(
        [Z2, "--out", "/app/output/k7_trace.json"],
        check=False,
        timeout=RUN_TIMEOUT,
    )
    assert bad.returncode != 0


def test_k25_transition_row_persist() -> None:
    """Scenario two transition live rows keep non-zero action_code after primary generations align."""
    _replay_through(2, emit=True)
    report = _load_report()
    s2_live = _rows_for(report, 2, "live")
    assert len(s2_live) >= 2
    spool = _active_row(_rows_for(report, 2, "spool"))
    live = _active_row(s2_live)
    assert spool["generation"] == live["generation"]
    assert any(int(r.get("action_code", 0)) != 0 for r in s2_live[1:])


def test_k26_hidden_epoch_overlay_store_keys() -> None:
    """Verifier-only s1 include overlay changes epoch material and digest-bearing store keys."""
    _reset_workspace()
    _apply_hidden_overlay(1)
    hidden_epoch, hidden_digest = _parse_frag(HIDDEN / "seq/s1/i0.frag")
    _replay_through(1, emit=True)
    _assert_metrics_leaf_epoch(hidden_epoch)
    joined = " ".join(p.name for p in STORE.glob("*.ward"))
    assert hidden_digest in joined
    report = _load_report()
    assert report["chain_fingerprint"] == _fingerprint(report["rows"])


def test_k27_rebuild_twice_idempotent() -> None:
    """Consecutive recover on unchanged WAL must not drift checkpoint seals or emit fingerprint."""
    _replay_through(3, emit=True)
    fp_before = _load_report()["chain_fingerprint"]
    assert subprocess.run([RECOVER], check=False, timeout=RUN_TIMEOUT).returncode == 0
    cp1 = json.loads((STATE / "checkpoint.json").read_text(encoding="utf-8"))
    assert subprocess.run([RECOVER], check=False, timeout=RUN_TIMEOUT).returncode == 0
    cp2 = json.loads((STATE / "checkpoint.json").read_text(encoding="utf-8"))
    assert cp1 == cp2
    _emit_report()
    assert _load_report()["chain_fingerprint"] == fp_before


def test_k28_double_report_stable() -> None:
    """Two consecutive emit runs on unchanged replay state must match chain_fingerprint."""
    _replay_through(4, emit=True)
    first = _load_report()["chain_fingerprint"]
    _emit_report()
    second = _load_report()["chain_fingerprint"]
    assert first == second
    assert first == _fingerprint(_load_report()["rows"])


def test_k29_line_order_fingerprint() -> None:
    """chain_fingerprint must use lexicographic row-line sort, not generation-only ordering."""
    _replay_through(4, emit=True)
    report = _load_report()
    lines = _row_lines(report["rows"])
    assert report["chain_fingerprint"] == _fingerprint(report["rows"])
    if _lines_differ_lex_vs_generation(lines):
        assert report["chain_fingerprint"] != _fingerprint_generation_order(lines)
