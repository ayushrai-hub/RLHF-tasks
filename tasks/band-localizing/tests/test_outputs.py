"""Verifier for the adiabatic-shear-band localization task.

Grades the committed shot plan on the WITHHELD characterization run: each alloy's band-in probability is
recomputed from the held-out true per-shot band rates, the joint worst-of-array floor is checked, and
committed cost is checked against the spend ceiling. EVERY grading constant (floor, capacity, ceiling,
rate range, per-alloy prices, and the true rates) is read only from verifier-only tests/ fixtures that are
never shipped in the image, so editing the agent-visible /app/data copies cannot relax the grade.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path("/app/output")

_truth = json.loads((HERE / "held_out_truth.json").read_text())
_thr = json.loads((HERE / "threshold.json").read_text())
_costs_tbl = json.loads((HERE / "costs.json").read_text())
FLOOR = float(_thr["band_floor"])
CAP = int(_thr["bar_capacity"])
# Sealed grading constant: the spend ceiling comes from the verifier-only fixture, NOT from the
# agent-editable /app/data/test_program.json.
SPEND_CEILING = float(_thr["spend_ceiling"])
# Sealed adopted-rate range: snapshotted into the verifier-only fixture so the rate bound the agent
# must respect cannot be relaxed by editing /app/data/test_program.json before verification.
RATE_MIN = float(_thr["rate_min"])
RATE_MAX = float(_thr["rate_max"])

PLAN_HEADER = ["alloy_id", "house_shots", "lab_shots", "adopted_rate"]


def _costs():
    """Per-alloy prices from the sealed verifier-only fixture (tests/costs.json), not /app/data."""
    c_ho = {p: float(v["cost_house"]) for p, v in _costs_tbl.items()}
    c_la = {p: float(v["cost_lab"]) for p, v in _costs_tbl.items()}
    return c_ho, c_la


def _as_int(value, name):
    """Require an exact (non-truncating) integer KPI; reject e.g. 10.9 silently floored to 10."""
    f = float(value)
    assert f == int(f), f"{name} must be an integer, got {value!r}"
    return int(f)


def _plan():
    """Load the agent's shot plan as {alloy_id: (house_shots, lab_shots)}."""
    plan = {}
    with open(OUT / "shot_plan.csv") as f:
        for r in csv.DictReader(f):
            plan[r["alloy_id"]] = (int(r["house_shots"]), int(r["lab_shots"]))
    return plan


def _rates():
    """Load the agent's adopted per-shot band rate per alloy as {alloy_id: adopted_rate}."""
    rates = {}
    with open(OUT / "shot_plan.csv") as f:
        for r in csv.DictReader(f):
            rates[r["alloy_id"]] = float(r["adopted_rate"])
    return rates


def test_plan_file_exists_and_parses():
    """The committed shot plan must exist with the required columns and parse cleanly."""
    p = OUT / "shot_plan.csv"
    assert p.exists(), "missing /app/output/shot_plan.csv"
    with open(p) as f:
        header = next(csv.reader(f))
    assert header == PLAN_HEADER, f"bad header: {header}"


def test_plan_has_exactly_one_row_per_alloy():
    """The raw CSV must hold exactly 40 data rows: the exact expected IDs, no duplicates.

    Validated on the raw rows (before any dict-loading) so duplicate alloy rows cannot be silently
    overwritten and pass.
    """
    with open(OUT / "shot_plan.csv") as f:
        rows = list(csv.DictReader(f))
    ids = [r["alloy_id"] for r in rows]
    assert len(ids) == 40, f"expected exactly 40 data rows, got {len(ids)}"
    assert len(set(ids)) == len(ids), f"duplicate alloy rows in plan: {ids}"
    assert set(ids) == set(_truth), "plan alloys do not match the expected A01..A40"


def test_all_alloys_covered_with_nonneg_integers():
    """Every alloy appears exactly once with non-negative integer shot counts."""
    plan = _plan()
    assert set(plan) == set(_truth), "plan alloys do not match the run"
    for pid, (ho, la) in plan.items():
        assert ho >= 0 and la >= 0, f"negative shots for {pid}"


def test_bar_capacity_respected():
    """Total in-house-bar shots across all alloys must not exceed the capacity."""
    plan = _plan()
    total_house = sum(ho for ho, _ in plan.values())
    assert total_house <= CAP, f"in-house-bar shots {total_house} exceed capacity {CAP}"


def test_adopted_rates_within_declared_range():
    """Every alloy's adopted per-shot band rate must be a real probability inside the declared range.

    The range bounds come from the sealed fixture, so editing /app/data cannot widen them.
    """
    rates = _rates()
    assert set(rates) == set(_truth), "adopted-rate rows do not match the run"
    for pid, p in rates.items():
        assert 0.0 < p <= 1.0, f"adopted_rate for {pid} is not a probability in (0, 1]: {p}"
        assert RATE_MIN <= p <= RATE_MAX, (
            f"adopted_rate for {pid} ({p}) is outside the declared range [{RATE_MIN}, {RATE_MAX}]"
        )


def test_committed_cost_within_ceiling():
    """Committed cost (priced from the sealed cost table) must not exceed the sealed spend ceiling."""
    plan = _plan()
    c_ho, c_la = _costs()
    cost = sum(c_ho[p] * ho + c_la[p] * la for p, (ho, la) in plan.items())
    assert cost <= SPEND_CEILING + 1e-6, (
        f"committed cost {cost:.2f} exceeds spend ceiling {SPEND_CEILING:.2f}"
    )


def test_worst_of_array_band_floor_met():
    """On the withheld characterization run, the weakest alloy must still clear the band floor.

    For each alloy, band-in probability = 1 - (1 - theta_true)^(house+lab). The run is accepted only if
    the minimum over all alloys is at least the floor (joint worst-of-array).
    """
    plan = _plan()
    worst = 1.0
    worst_pid = None
    for pid, theta in _truth.items():
        n = plan[pid][0] + plan[pid][1]
        prob = 1.0 - (1.0 - theta) ** n
        if prob < worst:
            worst, worst_pid = prob, pid
    assert worst >= FLOOR, (
        f"worst-of-array band-in prob {worst:.4f} (alloy {worst_pid}) is below floor {FLOOR}"
    )


def test_kpis_consistent_with_plan():
    """kpis.json totals, cost, and worst-alloy band prob must be consistent with the plan.

    worst_alloy_band_prob is checked for INTERNAL consistency only (the minimum over alloys of
    1 - (1 - adopted_rate)^(house + lab), from the agent's own columns), never against the withheld
    truth -- so the reported KPI is a verifiable function of the plan without leaking truth. Whether the
    adopted rates are good enough is decided by the worst-of-array floor test.
    """
    plan = _plan()
    rates = _rates()
    c_ho, c_la = _costs()
    kpis = json.loads((OUT / "kpis.json").read_text())
    tot_ho = sum(ho for ho, _ in plan.values())
    tot_la = sum(la for _, la in plan.values())
    cost = sum(c_ho[p] * ho + c_la[p] * la for p, (ho, la) in plan.items())
    assert _as_int(kpis["total_house_shots"], "total_house_shots") == tot_ho
    assert _as_int(kpis["total_lab_shots"], "total_lab_shots") == tot_la
    assert _as_int(kpis["total_committed_shots"], "total_committed_shots") == tot_ho + tot_la, (
        "total_committed_shots must equal total_house_shots + total_lab_shots"
    )
    assert abs(float(kpis["committed_cost"]) - cost) <= 0.5, "committed_cost inconsistent with plan"

    wp = float(kpis["worst_alloy_band_prob"])
    assert 0.0 <= wp <= 1.0, f"worst_alloy_band_prob {wp} is not a probability in [0, 1]"
    expected_wp = min(
        1.0 - (1.0 - rates[p]) ** (ho + la) for p, (ho, la) in plan.items()
    )
    assert abs(wp - expected_wp) <= 5e-3, (
        f"worst_alloy_band_prob {wp:.4f} does not match the value implied by the submitted "
        f"adopted_rate column and shot counts ({expected_wp:.4f}): it must equal the minimum over "
        "alloys of 1 - (1 - adopted_rate)^(house_shots + lab_shots)"
    )
