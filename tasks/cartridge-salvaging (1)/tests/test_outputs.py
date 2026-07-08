"""Verifier for the archival data-salvage cartridge task.

Grades the committed recovery plan on the live re-read: it recomputes each cartridge's recovery chance
from the held-out true per-pass read rates (never given to the agent), checks the joint worst-case
recovery floor, and checks committed cost against the cost ceiling. EVERY grading constant -- recovery
floor, bench capacity, cost ceiling, and the per-cartridge price table -- is read only from
verifier-only fixtures in tests/ (threshold.json, costs.json, held_out_truth.json), which never ship
in the image. The agent-visible copies under /app/data are informational and are never trusted for
grading, so an agent cannot relax a constraint by editing salvage_program.json or cartridges.csv
before verification. The held-out rates live only here, so the rates must be inferred from the sparse
read log and the read margin.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path("/app/output")

_truth = json.loads((HERE / "held_out_truth.json").read_text())
_thr = json.loads((HERE / "threshold.json").read_text())
_costs_tbl = json.loads((HERE / "costs.json").read_text())
FLOOR = float(_thr["recovery_floor"])
CAP = int(_thr["bench_capacity"])
# Sealed grading constant: the cost ceiling comes from the verifier-only fixture, NOT from the
# agent-editable /app/data/salvage_program.json.
COST_CEILING = float(_thr["cost_ceiling"])


def _costs():
    """Per-cartridge bench and lab pass prices from the sealed verifier-only fixture.

    Snapshotted from cartridges.csv at task-build time into tests/costs.json so grading cannot be
    relaxed by editing the agent-visible /app/data/cartridges.csv before verification.
    """
    c_bench = {s: float(v["cost_bench"]) for s, v in _costs_tbl.items()}
    c_lab = {s: float(v["cost_lab"]) for s, v in _costs_tbl.items()}
    return c_bench, c_lab


def _as_int(value, name):
    """Require an exact (non-truncating) integer KPI; reject e.g. 10.9 silently floored to 10."""
    f = float(value)
    assert f == int(f), f"{name} must be an integer, got {value!r}"
    return int(f)


def _plan():
    """Load the agent's recovery plan as {cartridge_id: (bench_passes, lab_passes)}."""
    plan = {}
    with open(OUT / "recovery_plan.csv") as f:
        for r in csv.DictReader(f):
            plan[r["cartridge_id"]] = (int(r["bench_passes"]), int(r["lab_passes"]))
    return plan


def test_plan_file_exists_and_parses():
    """The committed plan must exist with the required columns and parse cleanly."""
    p = OUT / "recovery_plan.csv"
    assert p.exists(), "missing /app/output/recovery_plan.csv"
    with open(p) as f:
        header = next(csv.reader(f))
    assert header == ["cartridge_id", "bench_passes", "lab_passes"], f"bad header: {header}"


def test_plan_has_exactly_one_row_per_cartridge():
    """The raw CSV must hold exactly 40 data rows: the expected IDs, no duplicates.

    Validated on the raw rows (before any dict-loading) so duplicate cartridge rows cannot be silently
    overwritten and pass.
    """
    with open(OUT / "recovery_plan.csv") as f:
        rows = list(csv.DictReader(f))
    ids = [r["cartridge_id"] for r in rows]
    assert len(ids) == 40, f"expected exactly 40 data rows, got {len(ids)}"
    assert len(set(ids)) == len(ids), f"duplicate cartridge rows in plan: {ids}"
    assert set(ids) == set(_truth), "plan cartridges do not match the expected T01..T40"


def test_all_cartridges_covered_with_nonneg_integers():
    """Every cartridge appears exactly once with non-negative integer pass counts."""
    plan = _plan()
    assert set(plan) == set(_truth), "plan cartridges do not match the batch"
    for cid, (bench, lab) in plan.items():
        assert bench >= 0 and lab >= 0, f"negative passes for {cid}"


def test_bench_capacity_respected():
    """Total bench passes across all cartridges must not exceed the capacity."""
    plan = _plan()
    total_bench = sum(bench for bench, _ in plan.values())
    assert total_bench <= CAP, f"bench passes {total_bench} exceed capacity {CAP}"


def test_committed_cost_within_ceiling():
    """Committed cost (priced from the sealed cost table) must not exceed the sealed cost ceiling."""
    plan = _plan()
    c_bench, c_lab = _costs()
    cost = sum(c_bench[s] * bench + c_lab[s] * lab for s, (bench, lab) in plan.items())
    assert cost <= COST_CEILING + 1e-6, (
        f"committed cost {cost:.2f} exceeds cost ceiling {COST_CEILING:.2f}"
    )


def test_worst_case_recovery_floor_met():
    """On the live re-read, the weakest cartridge must still clear the recovery floor.

    For each cartridge, recovery chance = 1 - (1 - rate_true)^(bench+lab). The plan is met only if the
    minimum over all cartridges is at least the floor (joint worst case).
    """
    plan = _plan()
    worst = 1.0
    worst_cid = None
    for cid, theta in _truth.items():
        n = plan[cid][0] + plan[cid][1]
        recovery = 1.0 - (1.0 - theta) ** n
        if recovery < worst:
            worst, worst_cid = recovery, cid
    assert worst >= FLOOR, (
        f"worst-case recovery chance {worst:.4f} (cartridge {worst_cid}) is below floor {FLOOR}"
    )


def test_kpis_consistent_with_plan():
    """kpis.json must report totals, cost, and worst-cartridge recovery chance consistent with the plan."""
    plan = _plan()
    c_bench, c_lab = _costs()
    kpis = json.loads((OUT / "kpis.json").read_text())
    tot_bench = sum(bench for bench, _ in plan.values())
    tot_lab = sum(lab for _, lab in plan.values())
    cost = sum(c_bench[s] * bench + c_lab[s] * lab for s, (bench, lab) in plan.items())
    assert _as_int(kpis["total_bench_passes"], "total_bench_passes") == tot_bench
    assert _as_int(kpis["total_lab_passes"], "total_lab_passes") == tot_lab
    assert _as_int(kpis["total_committed_passes"], "total_committed_passes") == tot_bench + tot_lab, (
        "total_committed_passes must equal total_bench + total_lab"
    )
    assert abs(float(kpis["committed_cost"]) - cost) <= 0.5, "committed_cost inconsistent with plan"
    # worst_cartridge_recovery_prob is the agent's own estimate -- it cannot see the held-out true read
    # rates, so this is NEVER cross-checked against truth. It must be a valid probability, and it must
    # be self-consistent with the plan's own claim of clearing the recovery floor: a plan that asserts
    # the weakest cartridge reaches the floor cannot honestly report a worst-cartridge recovery chance
    # below it. This rejects a fabricated or placeholder value (e.g. 0.0) without reading the hidden rates.
    ws = float(kpis["worst_cartridge_recovery_prob"])
    assert 0.0 <= ws <= 1.0, f"worst_cartridge_recovery_prob {ws} is not a probability in [0, 1]"
    assert ws >= FLOOR - 0.05, (
        f"worst_cartridge_recovery_prob {ws:.4f} is below the recovery floor {FLOOR:.4f} "
        "the plan claims to meet"
    )
