"""Verifier for stream-stats cold vs continued numeric and generation parity."""

import json
import subprocess
from pathlib import Path

BIN = "/usr/local/bin/stream-stats"
APP = Path("/app")
ENV = Path("/app/environment")
OUT = APP / "output"
VAR = APP / "var"
DUR_FRAME = VAR / "dur_frame.bin"
WAL_SEGMENT = VAR / "wal_segment.jsonl"
REUSE_STATE = VAR / "reuse_state.json"
FENCE_JOURNAL = VAR / "fence_journal.jsonl"
COLD_SNAP = VAR / "cold_report.json"
RUN_REPORT = OUT / "run_report.json"
MERGE_TRACE = OUT / "merge_trace.jsonl"
RESUME_DIFF = OUT / "resume_diff_summary.json"
FIXTURES = ENV / "fixtures"

TAIL_CAP = 12
MEAN_ABS = 1e-12
MOMENT_REL = 1e-9
QUANT_ABS = 1e-8
# Pre-merge partial sums can differ by a few ULPs across cold vs warm reduction order.
BRANCH_ABS = 1e-12


def _fixture_for_seed(seed: int) -> Path:
    name = "events_seed_a.tsv" if seed % 2 == 0 else "events_seed_b.tsv"
    return FIXTURES / name


def _load_events(seed: int) -> list[tuple[str, str, int, int, float]]:
    rows: list[tuple[str, str, int, int, float]] = []
    raw = _fixture_for_seed(seed).read_text(encoding="utf-8")
    for i, line in enumerate(raw.splitlines()):
        if i == 0 or not line.strip():
            continue
        branch, part, seq, ev_time, value = line.split("\t")
        rows.append((branch, part, int(seq), int(ev_time), float(value)))
    return rows


def _insert_tail(
    entries: list[tuple[int, int, float]], ev_time: int, seq: int, value: float
) -> None:
    entries.append((ev_time, seq, value))
    entries.sort(key=lambda x: (x[0], x[1]))
    if len(entries) > TAIL_CAP:
        del entries[: len(entries) - TAIL_CAP]


def _fuse_rank(
    left: list[tuple[int, int, float]], right: list[tuple[int, int, float]]
) -> list[tuple[int, int, float]]:
    out = list(left) + list(right)
    out.sort(key=lambda x: (x[0], x[1]))
    if len(out) > TAIL_CAP:
        out = out[-TAIL_CAP:]
    return out


def _fold_step(
    state: dict,
    value: float,
    ev_time: int = 0,
    seq: int = 0,
) -> None:
    n1 = state["n"]
    state["n"] += 1
    n = state["n"]
    mean_old = 0.0 if n1 == 0 else state["s"] / n1
    delta = value - mean_old
    mean_new = mean_old + delta / n
    delta2 = value - mean_new
    state["m"] += delta * delta2
    state["s"] += value
    state["vals"].append(value)
    _insert_tail(state["tail"], ev_time, seq, value)


def _combine_rank(pid: str, seq_hi: int) -> int:
    h = 0
    for b in pid.encode():
        h = (h * 131 + b) & 0xFFFFFFFFFFFFFFFF
    return (h * 1_000_000_000 + seq_hi) & 0xFFFFFFFFFFFFFFFF


def _branch_from_rows(rows: list[tuple[str, str, int, int, float]]) -> tuple[str, str, int, dict]:
    state = {"n": 0, "s": 0.0, "m": 0.0, "vals": [], "tail": []}
    seq_hi = 0
    pid = ""
    branch_id = ""
    for branch, part, seq, ev_time, value in rows:
        _fold_step(state, value, ev_time, seq)
        seq_hi = max(seq_hi, seq)
        pid = part
        branch_id = branch
    return branch_id, pid, seq_hi, state


def _merge_ordered(
    left: tuple[str, str, int, dict], right: tuple[str, str, int, dict]
) -> tuple[str, str, int, dict]:
    if _combine_rank(left[1], left[2]) <= _combine_rank(right[1], right[2]):
        first, second = left, right
    else:
        first, second = right, left
    fb, fp, fs, fst = first
    _sb, _sp, ss, sst = second
    merged = {
        "n": fst["n"],
        "s": fst["s"],
        "m": fst["m"],
        "vals": list(fst["vals"]),
        "tail": list(fst["tail"]),
    }
    for v in sst["vals"]:
        _fold_step(merged, v)
    merged["tail"] = _fuse_rank(fst["tail"], sst["tail"])
    return fb, fp, max(fs, ss), merged


def _parallel_merge(
    branches: list[tuple[str, str, int, dict]],
) -> tuple[str, str, int, dict]:
    work = sorted(branches, key=lambda b: _combine_rank(b[1], b[2]))
    while len(work) > 1:
        left = work.pop(0)
        right = work.pop(0)
        work.append(_merge_ordered(left, right))
    return work[0]


def _quantile_from_pool(entries: list[tuple[int, int, float]], q: float) -> float:
    if not entries:
        return 0.0
    vals = sorted(v for _t, _s, v in entries)
    idx = round((len(vals) - 1) * q)
    return vals[min(idx, len(vals) - 1)]


def _plan_digest(plan: list[str]) -> str:
    h = 0xCBF29CE484222325
    for name in plan:
        for b in name.encode():
            h ^= b
            h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
        h ^= 0xFF
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"{h:016x}"


def _oracle_report(events: list[tuple[str, str, int, int, float]], seed: int) -> dict:
    by_branch: dict[str, list[tuple[str, str, int, int, float]]] = {}
    for branch, part, seq, ev_time, value in events:
        by_branch.setdefault(branch, []).append((branch, part, seq, ev_time, value))
    branches = [
        _branch_from_rows(by_branch[bid]) for bid in sorted(by_branch.keys())
    ]
    plan = [
        b[0]
        for b in sorted(branches, key=lambda b: (_combine_rank(b[1], b[2]), b[0]))
    ]
    _branch, _pid, _seq_hi, st = _parallel_merge(branches)
    count_events = len(events)
    sum_events = sum(value for *_rest, value in events)
    mean = st["s"] / st["n"] if st["n"] else 0.0
    var = st["m"] / (st["n"] - 1) if st["n"] > 1 else 0.0
    stddev = (max(var, 0.0)) ** 0.5
    by_branch_tot: dict[str, float] = {}
    for branch, _part, _seq, _ev_time, value in events:
        by_branch_tot[branch] = by_branch_tot.get(branch, 0.0) + value
    branch_totals = [{"branch_id": k, "total": v} for k, v in sorted(by_branch_tot.items())]
    global_total = sum(by_branch_tot.values())
    return {
        "seed": seed,
        "profile": "oracle",
        "metrics": {
            "count": {"value": float(count_events), "tol_class": "exact"},
            "sum": {"value": sum_events, "tol_class": "exact"},
            "mean": {"value": mean, "tol_class": "mean_abs"},
            "var": {"value": var, "tol_class": "moment_rel"},
            "stddev": {"value": stddev, "tol_class": "moment_rel"},
            "p50": {"value": _quantile_from_pool(st["tail"], 0.50), "tol_class": "quant_abs"},
            "p95": {"value": _quantile_from_pool(st["tail"], 0.95), "tol_class": "quant_abs"},
            "p99": {"value": _quantile_from_pool(st["tail"], 0.99), "tol_class": "quant_abs"},
        },
        "global_total": global_total,
        "branch_totals": branch_totals,
        "observed_merge_steps": 0,
        "plan_digest": _plan_digest(plan),
    }


def _within(name: str, ref: float, got: float) -> bool:
    abs_d = abs(ref - got)
    if name in ("count", "sum"):
        return ref == got
    if name == "mean":
        return abs_d <= MEAN_ABS
    if name in ("var", "stddev"):
        denom = max(abs(ref), 1e-15)
        return abs_d / denom <= MOMENT_REL
    if name in ("p50", "p95", "p99"):
        return abs_d <= QUANT_ABS
    return abs_d <= MEAN_ABS


def _near_branch(ref: float, got: float) -> bool:
    return abs(ref - got) <= BRANCH_ABS * max(abs(ref), 1.0)


def _assert_report_near(expected: dict, got: dict) -> None:
    for name, cell in expected["metrics"].items():
        gcell = got["metrics"][name]
        assert _within(name, cell["value"], gcell["value"]), (
            f"{name}: expected {cell['value']} got {gcell['value']}"
        )
    assert _near_branch(expected["global_total"], got["global_total"]), (
        f"global_total: expected {expected['global_total']} got {got['global_total']}"
    )
    exp_map = {b["branch_id"]: b["total"] for b in expected["branch_totals"]}
    got_map = {b["branch_id"]: b["total"] for b in got["branch_totals"]}
    assert exp_map.keys() == got_map.keys()
    for bid, total in exp_map.items():
        assert _near_branch(total, got_map[bid]), (
            f"branch {bid}: expected {total} got {got_map[bid]}"
        )


def _assert_branch_totals_near(expected: dict, got: dict) -> None:
    assert _near_branch(expected["global_total"], got["global_total"])
    exp_map = {b["branch_id"]: b["total"] for b in expected["branch_totals"]}
    got_map = {b["branch_id"]: b["total"] for b in got["branch_totals"]}
    assert exp_map.keys() == got_map.keys()
    for bid, total in exp_map.items():
        assert _near_branch(total, got_map[bid])
    # Healthy runs keep partial-sum global_total aligned with the fixture-derived sum metric.
    assert _near_branch(got["global_total"], got["metrics"]["sum"]["value"])


def _clear_outputs() -> None:
    for p in (RUN_REPORT, MERGE_TRACE, RESUME_DIFF):
        if p.exists():
            p.unlink()


def _reset_durable() -> None:
    for p in (DUR_FRAME, WAL_SEGMENT, REUSE_STATE, COLD_SNAP, FENCE_JOURNAL):
        if p.exists():
            p.unlink()


def _run(*args: str) -> None:
    subprocess.run(
        ["bash", str(ENV / "scripts" / "prep_run.sh")],
        check=True,
        timeout=30,
    )
    subprocess.run([BIN, *args], check=True, timeout=120)


def _cold(seed: int) -> dict:
    _clear_outputs()
    _run("run", "--profile", "cold", "--seed", str(seed))
    return json.loads(RUN_REPORT.read_text(encoding="utf-8"))


def _warm(seed: int) -> dict:
    _clear_outputs()
    _run("resume", "--from-checkpoint", str(DUR_FRAME), "--seed", str(seed))
    return json.loads(RUN_REPORT.read_text(encoding="utf-8"))


def _load_trace() -> list[dict]:
    rows = []
    for line in MERGE_TRACE.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _load_diff() -> dict:
    return json.loads(RESUME_DIFF.read_text(encoding="utf-8"))


def _trace_pairs(trace: list[dict]) -> list[tuple[str, str]]:
    pairs = []
    for row in trace:
        left = row["left_branch"]
        right = row["right_branch"]
        pairs.append((left, right) if left <= right else (right, left))
    return sorted(pairs)


def _trace_ranks(trace: list[dict]) -> list[int]:
    return [row["combine_rank"] for row in trace]


def _wal_seal_peak() -> int:
    peak = 0
    if not WAL_SEGMENT.exists():
        return 0
    for line in WAL_SEGMENT.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        peak = max(peak, int(rec.get("seal_gen", 0)))
    return peak


def _fence_gen_for_seed(seed: int) -> int:
    if not FENCE_JOURNAL.exists():
        return 0
    last = 0
    for line in FENCE_JOURNAL.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if int(rec.get("seed", -1)) == seed:
            last = int(rec.get("frame_gen", 0))
    return last


def _corrupt_wal_mid() -> None:
    lines = WAL_SEGMENT.read_text(encoding="utf-8").splitlines()
    assert len(lines) >= 2
    lines.insert(len(lines) // 2, '{"seal_gen":1,"event":{"branch_id":"bad"')
    WAL_SEGMENT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _inject_foreign_wal(frame_gen: int) -> None:
    lines = WAL_SEGMENT.read_text(encoding="utf-8").splitlines()
    foreign = {
        "seal_gen": frame_gen + 99,
        "event": {
            "branch_id": "Z-foreign",
            "part_id": "p-foreign",
            "seq": 999999,
            "ev_time": 1,
            "value": 1.0e9,
        },
    }
    lines.insert(0, "not-json-at-all")
    lines.insert(1, json.dumps(foreign))
    lines.insert(len(lines) // 2, '{"seal_gen":')
    WAL_SEGMENT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_full_run_reference_parity() -> None:
    """Full run metrics must match the independent replay oracle within bands."""
    _reset_durable()
    for seed in (42, 1002):
        events = _load_events(seed)
        expected = _oracle_report(events, seed)
        got = _cold(seed)
        _assert_report_near(expected, got)
        assert isinstance(got["plan_digest"], str)
        assert len(got["plan_digest"]) == 16


def test_warm_parity_all_metrics() -> None:
    """Continued run must match the full run for the same seed on all published metrics."""
    _reset_durable()
    seed = 42
    cold = _cold(seed)
    warm = _warm(seed)
    _assert_report_near(cold, warm)
    assert warm["plan_digest"] == cold["plan_digest"]
    assert warm["frame_gen"] == cold["frame_gen"]


def test_frame_gen_seal_lock() -> None:
    """Resume diff seal_gen, fence journal, and WAL peak must match active frame generation."""
    _reset_durable()
    seed = 99
    cold = _cold(seed)
    warm = _warm(seed)
    diff = _load_diff()
    assert warm["frame_gen"] == cold["frame_gen"]
    assert diff["frame_gen"] == cold["frame_gen"]
    assert diff["seal_gen"] == cold["frame_gen"]
    assert _wal_seal_peak() == cold["frame_gen"]
    assert _fence_gen_for_seed(seed) == cold["frame_gen"]


def test_drain_watermark_frame_gen_lock() -> None:
    """Durable reuse drain_wm must equal frame_gen after each continue."""
    _reset_durable()
    seed = 99
    cold = _cold(seed)
    _warm(seed)
    state = json.loads(REUSE_STATE.read_text(encoding="utf-8"))
    assert state["drain_wm"] == cold["frame_gen"]
    assert state["frame_gen"] == cold["frame_gen"]
    diff = _load_diff()
    assert diff["drain_wm"] == cold["frame_gen"]


def test_chained_continue_invariants() -> None:
    """Four chained continues must plateau metrics and keep plan/trace ranks stable."""
    _reset_durable()
    seed = 99
    cold = _cold(seed)
    _clear_outputs()
    _run("run", "--profile", "cold", "--seed", str(seed))
    cold_ranks = _trace_ranks(_load_trace())
    reports = [_warm(seed) for _ in range(4)]
    _assert_report_near(cold, reports[0])
    anchor = reports[0]
    for rep in reports[1:]:
        for key in ("mean", "var", "stddev", "p50", "p95", "p99", "sum"):
            assert anchor["metrics"][key]["value"] == rep["metrics"][key]["value"]
        assert rep["plan_digest"] == cold["plan_digest"]
        assert rep["frame_gen"] == cold["frame_gen"]
    warm_ranks = _trace_ranks(_load_trace())
    assert warm_ranks == cold_ranks


def test_wal_mid_corruption_double_continue() -> None:
    """Malformed WAL mid-line then two continues must still match the full run."""
    _reset_durable()
    seed = 99
    cold = _cold(seed)
    _corrupt_wal_mid()
    first = _warm(seed)
    second = _warm(seed)
    _assert_report_near(cold, first)
    _assert_report_near(cold, second)
    diff = _load_diff()
    assert all(d["within_band"] for d in diff["metric_deltas"])
    assert diff["seal_gen"] == cold["frame_gen"]


def test_wal_gen_filter_after_corruption() -> None:
    """Salvage must keep seal_gen filtering: foreign-generation rows must not alter metrics."""
    _reset_durable()
    seed = 99
    cold = _cold(seed)
    _inject_foreign_wal(cold["frame_gen"])
    warm = _warm(seed)
    _assert_report_near(cold, warm)
    assert warm["metrics"]["sum"]["value"] == cold["metrics"]["sum"]["value"]


def test_inter_seed_durable_isolation() -> None:
    """Continue must match a seed's latest full run after another seed overwrote durable state."""
    _reset_durable()
    first_cold = _cold(42)
    _cold(99)
    second_cold = _cold(42)
    _assert_report_near(first_cold, second_cold)
    warm = _warm(42)
    _assert_report_near(second_cold, warm)
    assert warm["frame_gen"] == second_cold["frame_gen"]
    assert warm["plan_digest"] == second_cold["plan_digest"]
    diff = _load_diff()
    assert diff["frame_gen"] == second_cold["frame_gen"]
    assert diff["seal_gen"] == second_cold["frame_gen"]


def test_stale_plan_after_seed_swap() -> None:
    """After seed swap, continue must not reuse the prior seed's plan digest."""
    _reset_durable()
    a = _cold(42)
    b = _cold(99)
    assert a["plan_digest"] != b["plan_digest"] or a["frame_gen"] != b["frame_gen"]
    warm_b = _warm(99)
    assert warm_b["plan_digest"] == b["plan_digest"]
    assert warm_b["frame_gen"] == b["frame_gen"]
    _assert_report_near(b, warm_b)


def test_warm_cold_warm_trace_triangle() -> None:
    """Full, continue, full, and second continue must agree on metrics, plan, and trace."""
    _reset_durable()
    seed = 42
    first_cold = _cold(seed)
    cold_ranks = _trace_ranks(_load_trace())
    cold_pairs = _trace_pairs(_load_trace())
    first_warm = _warm(seed)
    _assert_report_near(first_cold, first_warm)
    assert first_warm["plan_digest"] == first_cold["plan_digest"]
    assert _trace_ranks(_load_trace()) == cold_ranks
    assert _trace_pairs(_load_trace()) == cold_pairs
    second_cold = _cold(seed)
    _assert_report_near(first_cold, second_cold)
    assert second_cold["plan_digest"] == first_cold["plan_digest"]
    second_warm = _warm(seed)
    _assert_report_near(first_cold, second_warm)
    assert second_warm["plan_digest"] == first_cold["plan_digest"]
    assert _trace_ranks(_load_trace()) == cold_ranks
    assert _trace_pairs(_load_trace()) == cold_pairs
    assert second_warm["observed_merge_steps"] == first_cold["observed_merge_steps"]


def test_late_event_cache_invalidation() -> None:
    """Odd-seed late arrivals must not reuse stale reuse slots across two continues."""
    _reset_durable()
    seed = 99
    _cold(seed)
    first = _warm(seed)
    diff1 = _load_diff()
    assert all(d["within_band"] for d in diff1["metric_deltas"])
    second = _warm(seed)
    diff2 = _load_diff()
    assert all(d["within_band"] for d in diff2["metric_deltas"])
    for key in ("var", "p95"):
        assert first["metrics"][key]["value"] == second["metrics"][key]["value"]


def test_precision_sensitive_moments() -> None:
    """Second-moment and tail metrics must survive durable frame hydrate without narrowing."""
    _reset_durable()
    seed = 1002
    events = _load_events(seed)
    expected = _oracle_report(events, seed)
    cold = _cold(seed)
    warm = _warm(seed)
    for key in ("var", "stddev", "p95", "p99"):
        assert _within(key, expected["metrics"][key]["value"], cold["metrics"][key]["value"])
        assert _within(key, expected["metrics"][key]["value"], warm["metrics"][key]["value"])
        assert _within(key, cold["metrics"][key]["value"], warm["metrics"][key]["value"])


def test_cross_artifact_generation_consistency() -> None:
    """Run report, resume_diff, reuse_state, fence, and WAL peak must agree on generation fields."""
    _reset_durable()
    seed = 42
    cold = _cold(seed)
    warm = _warm(seed)
    diff = _load_diff()
    state = json.loads(REUSE_STATE.read_text(encoding="utf-8"))
    assert warm["frame_gen"] == cold["frame_gen"]
    assert diff["frame_gen"] == warm["frame_gen"]
    assert diff["seal_gen"] == warm["frame_gen"]
    assert diff["drain_wm"] == warm["frame_gen"]
    assert diff["plan_digest"] == warm["plan_digest"]
    assert state["frame_gen"] == warm["frame_gen"]
    assert state["drain_wm"] == warm["frame_gen"]
    assert _wal_seal_peak() == warm["frame_gen"]
    assert _fence_gen_for_seed(seed) == warm["frame_gen"]


def test_reuse_epoch_monotone_across_continues() -> None:
    """Persisted reuse epoch must strictly increase across back-to-back continues."""
    _reset_durable()
    seed = 99
    _cold(seed)
    _warm(seed)
    assert REUSE_STATE.exists()
    first_epoch = json.loads(REUSE_STATE.read_text(encoding="utf-8"))["epoch"]
    _warm(seed)
    second_epoch = json.loads(REUSE_STATE.read_text(encoding="utf-8"))["epoch"]
    assert second_epoch > first_epoch
    diff = _load_diff()
    assert all(d["within_band"] for d in diff["metric_deltas"])


def test_combine_rank_sequence_parity() -> None:
    """Cold and continued runs must emit the same combine_rank sequence in file order."""
    _reset_durable()
    seed = 42
    _clear_outputs()
    _run("run", "--profile", "cold", "--seed", str(seed))
    cold_ranks = _trace_ranks(_load_trace())
    _clear_outputs()
    _run("resume", "--from-checkpoint", str(DUR_FRAME), "--seed", str(seed))
    warm_ranks = _trace_ranks(_load_trace())
    assert cold_ranks == warm_ranks
    assert len(cold_ranks) >= 1
    assert all(warm_ranks[i] <= warm_ranks[i + 1] for i in range(len(warm_ranks) - 1))


def test_plan_digest_survives_seed_swap_corruption_chain() -> None:
    """Plan digest must survive seed swap, WAL corruption, and a second continue."""
    _reset_durable()
    a = _cold(42)
    b = _cold(99)
    _corrupt_wal_mid()
    warm_b = _warm(99)
    assert warm_b["plan_digest"] == b["plan_digest"]
    assert warm_b["frame_gen"] == b["frame_gen"]
    _assert_report_near(b, warm_b)
    second = _warm(99)
    assert second["plan_digest"] == b["plan_digest"]
    assert second["observed_merge_steps"] == b["observed_merge_steps"]
    _assert_report_near(b, second)
    # Prior seed must not leak into the active plan after the swap chain.
    assert second["plan_digest"] != a["plan_digest"] or second["frame_gen"] != a["frame_gen"]


def test_branch_total_shadow_after_interleaved_salvage() -> None:
    """Branch totals and global_total must stay exact through salvage and seed interleaving."""
    _reset_durable()
    cold_a = _cold(42)
    _cold(99)
    cold_a2 = _cold(42)
    _inject_foreign_wal(cold_a2["frame_gen"])
    warm_a = _warm(42)
    _assert_branch_totals_near(cold_a, warm_a)
    _assert_branch_totals_near(cold_a2, warm_a)
    assert warm_a["metrics"]["sum"]["value"] == cold_a["metrics"]["sum"]["value"]


def test_triple_seed_corruption_recovery_matrix() -> None:
    """Three-seed matrix with mid-chain WAL corruption must keep each seed's continue correct."""
    _reset_durable()
    c42 = _cold(42)
    _cold(99)
    c1002 = _cold(1002)
    _corrupt_wal_mid()
    w1002 = _warm(1002)
    _assert_report_near(c1002, w1002)
    assert w1002["plan_digest"] == c1002["plan_digest"]
    # Re-seal 99 and continue after foreign rows from the prior corruption path.
    c99b = _cold(99)
    _inject_foreign_wal(c99b["frame_gen"])
    w99 = _warm(99)
    _assert_report_near(c99b, w99)
    assert w99["frame_gen"] == c99b["frame_gen"]
    assert _fence_gen_for_seed(99) == c99b["frame_gen"]
    # 42 must be re-established from a fresh full run, not stale durable bytes.
    c42b = _cold(42)
    cold_pairs = _trace_pairs(_load_trace())
    w42 = _warm(42)
    _assert_report_near(c42b, w42)
    assert w42["plan_digest"] == c42["plan_digest"]
    assert _trace_pairs(_load_trace()) == cold_pairs


def test_long_workflow_epoch_fence_lock() -> None:
    """Long mixed-profile workflow must keep epoch monotone and fence/frame generations locked."""
    _reset_durable()
    seed = 99
    cold = _cold(seed)
    epochs = []
    for i in range(5):
        warm = _warm(seed)
        _assert_report_near(cold, warm)
        state = json.loads(REUSE_STATE.read_text(encoding="utf-8"))
        epochs.append(state["epoch"])
        assert state["drain_wm"] == cold["frame_gen"]
        assert state["frame_gen"] == cold["frame_gen"]
        assert _fence_gen_for_seed(seed) == cold["frame_gen"]
        diff = _load_diff()
        assert diff["seal_gen"] == cold["frame_gen"]
        assert diff["plan_digest"] == cold["plan_digest"]
        if i > 0:
            assert epochs[i] > epochs[i - 1]


def test_salvage_then_seed_swap_then_resume() -> None:
    """WAL salvage, then a different seed full run, then resume must follow the latest seal."""
    _reset_durable()
    _cold(42)
    _corrupt_wal_mid()
    _warm(42)
    b = _cold(99)
    warm_b = _warm(99)
    _assert_report_near(b, warm_b)
    assert warm_b["plan_digest"] == b["plan_digest"]
    assert warm_b["frame_gen"] == b["frame_gen"]
    assert _wal_seal_peak() == b["frame_gen"]
    assert _fence_gen_for_seed(99) == b["frame_gen"]
    # Fence for 99 must be the active seal; continuing 99 again must plateau.
    again = _warm(99)
    _assert_report_near(b, again)
    assert again["observed_merge_steps"] == b["observed_merge_steps"]


def test_metric_plateau_across_mixed_profiles() -> None:
    """Cold/warm/cold/warm/warm cycle must keep moment and quantile metrics identical."""
    _reset_durable()
    seed = 1002
    r0 = _cold(seed)
    r1 = _warm(seed)
    r2 = _cold(seed)
    r3 = _warm(seed)
    r4 = _warm(seed)
    for rep in (r1, r2, r3, r4):
        for key in ("mean", "var", "stddev", "p50", "p95", "p99", "sum"):
            assert _within(key, r0["metrics"][key]["value"], rep["metrics"][key]["value"])
        assert rep["plan_digest"] == r0["plan_digest"]
        _assert_branch_totals_near(r0, rep)


def test_interleaved_seed_continue_trace_lock() -> None:
    """After another seed overwrites durable state, continue must match that seed's trace."""
    _reset_durable()
    _cold(42)
    _cold(99)
    anchor = _cold(42)
    anchor_ranks = _trace_ranks(_load_trace())
    anchor_pairs = _trace_pairs(_load_trace())
    warm = _warm(42)
    _assert_report_near(anchor, warm)
    assert _trace_ranks(_load_trace()) == anchor_ranks
    assert _trace_pairs(_load_trace()) == anchor_pairs
    diff = _load_diff()
    assert diff["ordering_violations"] == 0
    assert diff["max_combine_rank"] == max(anchor_ranks)
    assert diff["plan_digest"] == anchor["plan_digest"]


def test_wal_salvage_full_continue_cycle() -> None:
    """After WAL corruption salvage, a fresh full run and continue must still match."""
    _reset_durable()
    seed = 99
    cold = _cold(seed)
    cold_pairs = _trace_pairs(_load_trace())
    lines = WAL_SEGMENT.read_text(encoding="utf-8").splitlines()
    lines.insert(0, "not-json-at-all")
    lines.insert(len(lines) // 2, '{"seal_gen":1,"event":')
    WAL_SEGMENT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    salvaged = _warm(seed)
    _assert_report_near(cold, salvaged)
    second_cold = _cold(seed)
    _assert_report_near(cold, second_cold)
    second_cold_pairs = _trace_pairs(_load_trace())
    second_warm = _warm(seed)
    _assert_report_near(second_cold, second_warm)
    assert _trace_pairs(_load_trace()) == second_cold_pairs
    assert second_cold_pairs == cold_pairs
    assert second_warm["frame_gen"] == second_cold["frame_gen"]
