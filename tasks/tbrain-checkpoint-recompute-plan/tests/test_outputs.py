"""Behavioral checks for the ckptplan activation-checkpointing planner.

`ckptplan plan` partitions an ordered layer list into contiguous segments whose
first layer is a retained checkpoint and whose remaining layers are recomputed
during the backward pass. The reported plan must use a peak-memory estimate that
combines the resident checkpoint memory (shared by every segment) with the
largest in-segment recompute working set, and it must select the feasible
segmentation that minimises recompute.

The reference below recomputes the ground truth independently by enumerating
every contiguous partition (the layer counts here are small), scoring each by
the cost model, and selecting the minimum-recompute feasible partition (with the
stated tie-breaks). It is intentionally not part of the shipped program; every
assertion is observable from `ckptplan` output alone.
"""

import json
import subprocess

import pytest

APP = "/app"
BIN = "/app/ckptplan"


def _build():
    """Build the ckptplan binary once for the whole module."""
    r = subprocess.run(
        ["go", "build", "-o", BIN, "./cmd/ckptplan"],
        cwd=APP,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert r.returncode == 0, f"go build failed:\n{r.stdout}\n{r.stderr}"


@pytest.fixture(scope="module", autouse=True)
def built():
    _build()


def _segments(bounds, n):
    for k, b in enumerate(bounds):
        end = bounds[k + 1] if k + 1 < len(bounds) else n
        yield b, end


def _score(layers, bounds):
    """Return (peak, recompute) for a partition under the cost model."""
    act = [a for a, _ in layers]
    rec = [r for _, r in layers]
    n = len(layers)
    checkpoint_sum = sum(act[b] for b in bounds)
    max_ws = 0
    recompute = 0
    for b, end in _segments(bounds, n):
        ws = sum(act[j] for j in range(b + 1, end))
        max_ws = max(max_ws, ws)
        recompute += sum(rec[j] for j in range(b + 1, end))
    return checkpoint_sum + max_ws, recompute


def reference(layers, budget):
    """Independent ground truth for the chosen plan and its reported numbers."""
    n = len(layers)
    total_act = sum(a for a, _ in layers)
    feasible_best = None  # (recompute, n_seg, bounds)
    lowest_peak = None  # (peak, n_seg, bounds)
    for mask in range(1 << (n - 1)):
        bounds = [0] + [i for i in range(1, n) if mask & (1 << (i - 1))]
        peak, recompute = _score(layers, bounds)
        cand_peak = (peak, len(bounds), bounds)
        if lowest_peak is None or cand_peak < lowest_peak:
            lowest_peak = cand_peak
        if peak <= budget:
            cand = (recompute, len(bounds), bounds)
            if feasible_best is None or cand < feasible_best:
                feasible_best = cand
    if feasible_best is not None:
        recompute, _, bounds = feasible_best
        peak, _ = _score(layers, bounds)
        return {
            "n_segments": len(bounds),
            "boundaries": bounds,
            "est_peak_mem": peak,
            "est_recompute": recompute,
            "total_activation": total_act,
            "feasible": True,
        }
    peak, _, bounds = lowest_peak
    _, recompute = _score(layers, bounds)
    return {
        "n_segments": len(bounds),
        "boundaries": bounds,
        "est_peak_mem": peak,
        "est_recompute": recompute,
        "total_activation": total_act,
        "feasible": False,
    }


def run_plan(layers, budget):
    """Run `ckptplan plan` on a layer list and return the parsed JSON object."""
    inp = "".join(f"{a} {r}\n" for a, r in layers)
    r = subprocess.run(
        [BIN, "plan", "--budget", str(budget)],
        input=inp,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert r.returncode == 0, f"ckptplan plan failed (rc={r.returncode}):\n{r.stderr}"
    return json.loads(r.stdout.strip())


def check(layers, budget):
    got = run_plan(layers, budget)
    want = reference(layers, budget)
    assert got == want, (
        f"\nlayers={layers} budget={budget}"
        f"\n  reported: {got}"
        f"\n  expected: {want}"
    )


# ---------------------------------------------------------------------------
# Group A: budgets that comfortably fit retaining everything.
# ---------------------------------------------------------------------------

def test_ample_budget_keeps_everything_resident():
    """When the budget covers every activation at once, retaining each layer on
    its own avoids all recompute, and the reported numbers must reflect that."""
    check([(5, 10), (10, 10)], 17)
    check([(4, 9), (7, 2), (5, 5)], 16)
    check([(1, 10), (2, 8)], 7)


def test_homogeneous_layers_ample_budget():
    """Uniform layers under a generous budget: the resident-only view of peak and
    the chosen plan happen to line up, so this must keep matching the model."""
    check([(4, 5), (4, 5), (4, 5), (4, 5)], 16)
    check([(3, 2), (3, 2), (3, 2)], 12)
    check([(6, 7), (6, 7), (6, 7), (6, 7), (6, 7)], 30)


# ---------------------------------------------------------------------------
# Group B: budgets below the cost of retaining everything -- recompute forced,
# the peak must include the in-segment working set, and the cheapest feasible
# partition is not the one that packs segments as full as the budget allows.
# ---------------------------------------------------------------------------

def test_peak_includes_in_segment_working_set():
    """A partition that keeps too much in one segment exceeds the budget through
    its working set even though its retained checkpoints are small; the reported
    peak must surface that and the plan must avoid it."""
    check([(4, 9), (6, 7), (6, 5), (2, 3), (2, 3), (8, 3)], 18)
    check([(3, 8), (7, 6), (8, 1), (3, 7), (7, 8), (5, 2)], 20)
    check([(10, 0), (1, 9), (1, 9), (10, 1), (1, 9), (1, 9)], 16)


def test_cheapest_feasible_is_not_the_fullest_packing():
    """The minimum-recompute feasible partition can split where a budget-filling
    walk would not, trading a slightly higher checkpoint total for a far smaller
    worst-segment working set; the chosen plan must be the true optimum."""
    check([(6, 0), (2, 9), (6, 1), (2, 9), (6, 1)], 14)
    check([(3, 0), (3, 7), (9, 1), (3, 7), (3, 7), (9, 1)], 18)
    check([(4, 0), (4, 10), (4, 3), (4, 10), (4, 3), (4, 10)], 14)
    check([(5, 6), (9, 2), (3, 8), (7, 1), (6, 9), (2, 4), (8, 3)], 24)


def test_tight_budget_infeasible_reports_lowest_peak():
    """When even the lowest-peak partition exceeds the budget, the plan is marked
    not feasible and reports that lowest-peak partition's own numbers, not a
    budget-filling walk's."""
    check([(5, 8), (5, 8), (5, 8), (5, 8), (5, 8)], 15)
    check([(4, 1), (9, 6), (1, 9)], 10)
    check([(8, 10), (9, 6), (6, 7), (10, 7), (6, 4)], 25)


# ---------------------------------------------------------------------------
# Group C: edges.
# ---------------------------------------------------------------------------

def test_single_layer():
    """One layer is always a single retained checkpoint with no recompute."""
    check([(7, 4)], 7)
    check([(7, 4)], 3)


def test_two_layers():
    """Two layers either both fit as checkpoints or collapse into one segment."""
    check([(9, 4), (2, 4)], 14)
    check([(9, 4), (2, 4)], 9)
    check([(6, 5), (6, 5)], 6)
