"""Verifier for stats-plan-resume-skew plan audit."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest

APP = Path(os.environ.get("TASK_APP_ROOT", "/app"))
AUDIT = APP / "output" / "plan_audit.json"
MANIFEST = APP / "data" / "scenarios" / "manifest.tsv"
CHECKSUM_MANIFEST = APP / "doc" / "input_checksums.txt"
PINNED_INTEGRITY = APP / "doc" / "pinned_integrity.txt"
BUILD_HOOK = APP / "ci" / "build_and_load.sh"
SCHEMA_STUB = APP / "stubs" / "schema_anchor.txt"
MATRIX_BIN = APP / "bin" / "plan_matrix"

ROW_KEYS = frozenset(
    {
        "scenario_id",
        "mode",
        "step_alpha_id",
        "step_beta_id",
        "step_gamma_id",
        "stats_gen",
        "stats_ok",
        "pair_ok",
        "plan_digest",
        "finish_reason",
    }
)

HARD_SCENARIO_IDS = frozenset(
    {
        "s_reload_mid",
        "s_memo_stale",
        "s_gen_skew",
        "s_join_flip",
        "s_triple_analyze",
        "s_nested_q",
        "s_lane_skew",
        "s_chain_analyze",
        "s_dual_fp",
        "s_partial_flip",
        "s_bucket_shift",
        "s_quad_analyze",
        "s_double_pause",
        "s_memo_rewind",
        "s_tie_carry",
        "s_snap_buckets",
    }
)

REQUIRED_IMPL_SITES: dict[str, str] = {
    "weave_u/slot_weft.c": "de9cc581d97fd533df9a59240b43ddfc764b2b09230418cd257c032aaffeeb9f",
    "weave_u/tie_fold.c": "e16ecf1e3c05c3e0c0f5eca65a269958aa6cd202c4d5887657ce7004ab9008da",
    "shard_k/lane_weft.c": "29e90376454dd6a5f2dd471dd6ade1b426a3de8e67c0a7a462a683f5be7bd02a",
    "shard_k/bound_lane.c": "559e0b62429516a2bbbe7092e6d4405b81ad39634c6442ae7f7c247039236711",
    "spool_q/ring_weft.c": "b558e273435df7dcb2b5812fb4933023cdabb9a49273f4ab164cc4ee1c2ae1ef",
    "spool_q/epoch_slot.c": "5436ec2607bdca43fece2094bd9e7be028aa1d7a312909764286e9032d869904",
    "vault_r/fold_weft.c": "2b71ce406e3581a6c3e02becd71cc201befe9f3e1a8a03550599bf6afe91480c",
    "vault_r/stamp_line.c": "f3feb21ea92b2ad36a9aaee1caa8c35e3eff8d936b3d5faeb6f509c8e222fc51",
}

BUGGY_MODULE_SHA256: dict[str, str] = {}
PINNED_NON_IMPL_SHA256: dict[str, str] = {}


def _load_pinned_integrity() -> dict[str, str]:
    entrypoints: dict[str, str] = {}
    for raw in PINNED_INTEGRITY.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        role, rel, digest = line.split()
        if role == "entrypoint":
            entrypoints[rel] = digest
    return entrypoints


@dataclass
class _Table:
    rows: int = 0
    distinct: int = 0
    buckets: int = 4
    bounds: list[int] = field(default_factory=lambda: [0, 0, 0, 0])
    stats_gen: int = 0


@dataclass
class _Ctx:
    tables: list[_Table] = field(default_factory=list)
    live_gen: int = 0
    vis_gen: int = 1
    snap_valid: bool = False
    snap_tables: list[_Table] = field(default_factory=list)
    snap_bounds: list[list[int]] = field(default_factory=list)
    snap_gen: int = 0
    snap_vis_gen: int = 1
    resume_pending: bool = False
    memo_fp: int = 0
    memo_gen: int = 0
    memo_alpha: str = ""
    memo_beta: str = ""
    memo_gamma: str = ""
    memo_valid: bool = False

    def ensure(self, table: int) -> _Table:
        while len(self.tables) <= table:
            self.tables.append(_Table())
        return self.tables[table]


def _fold_fp(tag: str) -> int:
    h = 1469598103934665603
    for ch in tag.encode():
        h ^= ch
        h = (h * 1099511628211) & ((1 << 64) - 1)
    return h


def _fold_hex(alpha: str, beta: str, gamma: str, gen: int) -> str:
    acc = (2166136261 ^ gen) & ((1 << 64) - 1)
    for part in (alpha, beta, gamma):
        for ch in part:
            acc = ((acc * 131) ^ ord(ch)) & ((1 << 64) - 1)
    return f"{acc:016x}"


def _merge_a(persisted: int, live: int) -> int:
    return live


def _est_b(live: _Table, snap: _Table | None, use_snap: bool, bucket: int) -> float:
    bound_src = snap if use_snap and snap is not None else live
    if live.buckets == 0:
        return 1.0
    hi = bound_src.bounds[bucket]
    if hi == 0:
        return 1.0
    return live.buckets / (hi + 1)


def _lookup(ctx: _Ctx, fp: int, gen: int) -> tuple[str, str, str] | None:
    if not ctx.memo_valid or ctx.memo_fp != fp or ctx.memo_gen != gen:
        return None
    return ctx.memo_alpha, ctx.memo_beta, ctx.memo_gamma


def _store(ctx: _Ctx, fp: int, gen: int, alpha: str, beta: str, gamma: str) -> None:
    ctx.memo_fp = fp
    ctx.memo_gen = gen
    ctx.memo_alpha = alpha
    ctx.memo_beta = beta
    ctx.memo_gamma = gamma
    ctx.memo_valid = True


def _probe(vis_gen: int, live_vis: int, row_est: int, partial_req: bool) -> bool:
    if not partial_req:
        return True
    return vis_gen == live_vis and row_est > 0


def _pick_join(sel0: float, sel1: float, rows0: int, rows1: int) -> tuple[str, str]:
    cost_nl = sel0 * rows1
    cost_hj = rows0 + rows1
    if cost_nl < cost_hj:
        return "nest_loop", "build_left"
    return "hash_join", "build_right"


def _drive(ctx: _Ctx, fp: int, partial_req: bool) -> tuple[str, str, str, int]:
    gen = ctx.live_gen
    if ctx.snap_valid and ctx.resume_pending:
        gen = _merge_a(ctx.snap_gen, ctx.live_gen)
    cached = _lookup(ctx, fp, gen)
    if cached is not None:
        return cached[0], cached[1], cached[2], gen
    t0 = ctx.tables[0] if ctx.tables else _Table()
    t1 = ctx.tables[1] if len(ctx.tables) > 1 else _Table()
    snap0 = ctx.snap_tables[0] if ctx.snap_valid and ctx.snap_tables else None
    use_snap = ctx.snap_valid and ctx.resume_pending
    sel0 = _est_b(t0, snap0, use_snap, 1)
    sel1 = _est_b(t1, snap0, use_snap, 2)
    alpha, beta = _pick_join(sel0, sel1, t0.rows, t1.rows)
    probe_vis = ctx.snap_vis_gen if ctx.resume_pending else ctx.vis_gen
    gamma = "partial_scan" if _probe(probe_vis, ctx.vis_gen, t0.rows, partial_req) else "seq_scan"
    _store(ctx, fp, gen, alpha, beta, gamma)
    return alpha, beta, gamma, gen


def _parse_line(line: str) -> tuple[str, dict[str, str]]:
    parts = line.strip().split()
    kind = parts[0]
    args: dict[str, str] = {}
    for tok in parts[1:]:
        if "=" in tok:
            k, v = tok.split("=", 1)
            args[k] = v
    return kind, args


def _gold_row(tape_path: Path, pause_mode: bool) -> dict[str, Any]:
    ctx = _Ctx()
    query_tag = "q0"
    partial_req = False
    result: dict[str, Any] | None = None
    for raw in tape_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        kind, args = _parse_line(line)
        if kind == "init":
            ctx.vis_gen = int(args.get("vis", "1"))
        elif kind == "load":
            table = int(args.get("table", "0"))
            t = ctx.ensure(table)
            t.rows = int(args.get("rows", "0"))
            t.distinct = int(args.get("distinct", "0"))
            t.buckets = int(args.get("buckets", "4"))
            for i in range(4):
                if f"b{i}" in args:
                    t.bounds[i] = int(args[f"b{i}"])
            t.stats_gen = ctx.live_gen
        elif kind == "analyze":
            table = int(args.get("table", "0"))
            t = ctx.ensure(table)
            old_rows = t.rows
            t.rows = int(args.get("rows", "0"))
            t.distinct = int(args.get("distinct", "0"))
            if old_rows > 0 and t.rows != old_rows:
                for i in range(4):
                    if t.bounds[i] > 0:
                        t.bounds[i] = (t.bounds[i] * t.rows) // old_rows
            ctx.live_gen += 1
            t.stats_gen = ctx.live_gen
        elif kind == "vis":
            ctx.vis_gen = int(args.get("gen", "1"))
        elif kind == "pause" and pause_mode:
            ctx.snap_valid = True
            ctx.snap_gen = ctx.live_gen
            ctx.snap_vis_gen = ctx.vis_gen
            ctx.snap_tables = [_Table(**t.__dict__) for t in ctx.tables]
            ctx.snap_bounds = [list(t.bounds) for t in ctx.tables]
        elif kind == "resume" and pause_mode:
            ctx.resume_pending = True
            for i, t in enumerate(ctx.tables):
                if i < len(ctx.snap_bounds):
                    t.bounds = list(ctx.snap_bounds[i])
        elif kind == "query":
            query_tag = args.get("fp", query_tag)
            partial_req = bool(int(args.get("partial", "0")))
            alpha, beta, gamma, gen = _drive(ctx, _fold_fp(query_tag), partial_req)
            ctx.resume_pending = False
            result = {
                "step_alpha_id": alpha,
                "step_beta_id": beta,
                "step_gamma_id": gamma,
                "stats_gen": gen,
                "stats_ok": gen == ctx.live_gen,
                "plan_digest": _fold_hex(alpha, beta, gamma, gen),
                "finish_reason": "ok",
            }
    if result is None:
        raise AssertionError(f"no query in {tape_path}")
    return result


def _gold_report() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    pair_mismatch = 0
    step_mismatch = 0
    for raw in MANIFEST.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if len(parts) != 2:
            continue
        sid, rel = parts
        tape = APP / rel
        cont = _gold_row(tape, pause_mode=False)
        cont.update({"scenario_id": sid, "mode": "continuous", "pair_ok": True})
        pause = _gold_row(tape, pause_mode=True)
        agree = (
            cont["step_alpha_id"] == pause["step_alpha_id"]
            and cont["step_beta_id"] == pause["step_beta_id"]
            and cont["step_gamma_id"] == pause["step_gamma_id"]
            and cont["stats_gen"] == pause["stats_gen"]
            and cont["plan_digest"] == pause["plan_digest"]
        )
        pause.update({"scenario_id": sid, "mode": "pause_resume", "pair_ok": agree})
        if not agree:
            pair_mismatch += 1
            for key in ("step_alpha_id", "step_beta_id", "step_gamma_id", "stats_gen"):
                if cont[key] != pause[key]:
                    step_mismatch += 1
        rows.extend([cont, pause])
    return {
        "schema_anchor": int(SCHEMA_STUB.read_text().strip()),
        "scenarios": rows,
        "summary": {
            "scenario_count": len(rows) // 2,
            "scenario_rows": len(rows),
            "pair_mismatch_count": pair_mismatch,
            "step_mismatch_total": step_mismatch,
        },
    }


def _sha256(path: Path) -> str:
    proc = subprocess.run(
        ["sha256sum", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return proc.stdout.split()[0]


@pytest.fixture(scope="session")
def built_audit() -> dict[str, Any]:
    subprocess.run([str(BUILD_HOOK)], check=True, cwd=str(APP), timeout=180)
    return json.loads(AUDIT.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def gold_audit() -> dict[str, Any]:
    return _gold_report()


def _row(audit: dict[str, Any], scenario_id: str, mode: str) -> dict[str, Any]:
    return next(
        r
        for r in audit["scenarios"]
        if r["scenario_id"] == scenario_id and r["mode"] == mode
    )


def test_frozen_inputs_unchanged() -> None:
    """Shipped tapes, docs, and harness entrypoints must match checksum manifest."""
    for raw in CHECKSUM_MANIFEST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rel, expected = line.split()
        target = APP / rel
        assert target.is_file(), rel
        assert _sha256(target) == expected, rel


def test_matrix_binary_is_elf(built_audit: dict[str, Any]) -> None:
    """Report must come from the compiled matrix binary."""
    assert built_audit["schema_anchor"] == int(SCHEMA_STUB.read_text().strip())
    header = MATRIX_BIN.read_bytes()[:4]
    assert header == b"\x7fELF"


def test_report_schema(built_audit: dict[str, Any]) -> None:
    """Top-level report shape matches plan_audit_contract."""
    assert built_audit["schema_anchor"] == 4207
    assert isinstance(built_audit["scenarios"], list)
    assert set(built_audit["summary"]) == {
        "scenario_count",
        "scenario_rows",
        "pair_mismatch_count",
        "step_mismatch_total",
    }
    for row in built_audit["scenarios"]:
        assert ROW_KEYS <= set(row)


def test_manifest_order(built_audit: dict[str, Any]) -> None:
    """Scenario rows follow manifest order with continuous then pause_resume."""
    expected: list[tuple[str, str]] = []
    for raw in MANIFEST.read_text(encoding="utf-8").splitlines():
        parts = raw.split()
        if len(parts) != 2:
            continue
        sid = parts[0]
        expected.append((sid, "continuous"))
        expected.append((sid, "pause_resume"))
    actual = [(r["scenario_id"], r["mode"]) for r in built_audit["scenarios"]]
    assert actual == expected


def test_summary_counters_clean(built_audit: dict[str, Any]) -> None:
    """A repaired tree clears mismatch counters in the summary block."""
    assert built_audit["summary"]["pair_mismatch_count"] == 0
    assert built_audit["summary"]["step_mismatch_total"] == 0


def test_all_pause_rows_pair_ok(built_audit: dict[str, Any]) -> None:
    """Every pause_resume row must agree with its continuous counterpart."""
    for row in built_audit["scenarios"]:
        if row["mode"] != "pause_resume":
            continue
        assert row["pair_ok"] is True, row["scenario_id"]
        cont = _row(built_audit, row["scenario_id"], "continuous")
        assert row["step_alpha_id"] == cont["step_alpha_id"]
        assert row["step_beta_id"] == cont["step_beta_id"]
        assert row["step_gamma_id"] == cont["step_gamma_id"]
        assert row["stats_gen"] == cont["stats_gen"]
        assert row["plan_digest"] == cont["plan_digest"]


def test_all_rows_stats_ok(built_audit: dict[str, Any]) -> None:
    """stats_ok must be true on every scenario row."""
    for row in built_audit["scenarios"]:
        assert row["stats_ok"] is True, row
        assert row["finish_reason"] == "ok"


@pytest.mark.parametrize("scenario_id", sorted(HARD_SCENARIO_IDS))
def test_hard_scenario_matches_replay(
    built_audit: dict[str, Any], gold_audit: dict[str, Any], scenario_id: str
) -> None:
    """Stress scenarios must match the independent replay model."""
    for mode in ("continuous", "pause_resume"):
        row = _row(built_audit, scenario_id, mode)
        gold = _row(gold_audit, scenario_id, mode)
        assert row == {**row, **{k: gold[k] for k in gold if k in ROW_KEYS}}


def test_matches_independent_replay(
    built_audit: dict[str, Any], gold_audit: dict[str, Any]
) -> None:
    """Full scenario table must match the replay-derived reference."""
    for i, row in enumerate(built_audit["scenarios"]):
        gold = gold_audit["scenarios"][i]
        for key in ROW_KEYS:
            assert row[key] == gold[key]


def test_report_byte_stable(built_audit: dict[str, Any]) -> None:
    """Repeated hook runs must emit identical JSON bytes."""
    first = AUDIT.read_bytes()
    subprocess.run([str(BUILD_HOOK)], check=True, cwd=str(APP), timeout=180)
    second = AUDIT.read_bytes()
    assert first == second


def test_non_impl_sources_pinned() -> None:
    """Frozen harness sources must not be rewritten."""
    entrypoints = _load_pinned_integrity()
    for rel, expected in entrypoints.items():
        path = APP / rel
        assert path.is_file(), rel
        assert _sha256(path) == expected, rel


def test_resume_impl_sites_repaired(built_audit: dict[str, Any]) -> None:
    """A passing audit must repair every nested resume-path module in the verifier set."""
    if built_audit["summary"]["pair_mismatch_count"] != 0:
        return
    unchanged = [
        rel
        for rel, digest in REQUIRED_IMPL_SITES.items()
        if _sha256(APP / rel) == digest
    ]
    assert not unchanged, f"resume-path modules still shipped: {unchanged}"


def test_stress_scenario_count(built_audit: dict[str, Any]) -> None:
    """Matrix must cover the full bundled scenario manifest."""
    assert built_audit["summary"]["scenario_count"] == 18
    assert built_audit["summary"]["scenario_rows"] == 36
