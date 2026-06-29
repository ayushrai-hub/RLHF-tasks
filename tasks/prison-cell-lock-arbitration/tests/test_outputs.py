import json
import subprocess
from pathlib import Path

import pytest

TRACE = Path("/app/output/failover_trace.json")
PLAN_SLICES = {"north-wing", "east-link", "yard-cross", "south-gate"}
AUDIT_HEAD = "5b58a1b91f119798254073d43b5a8ddc9d39717e16136ec9205e1528c9abe531"
BASELINE_OVERRIDE = 3
OUTCOME_CONVERGED = "converged"
OUTCOME_DELAYED_SKEW = "delayed_skew"


def regenerate_trace() -> dict:
    if TRACE.exists():
        TRACE.unlink()
    subprocess.run(
        ["bash", "/app/environment/scripts/run_sim_driver.sh"],
        check=True,
        timeout=600,
    )
    return json.loads(TRACE.read_text())


@pytest.fixture(scope="module")
def trace_doc() -> dict:
    return regenerate_trace()


def run_by_id(doc: dict, run_id: str) -> dict:
    for row in doc["runs"]:
        if row["run_id"] == run_id:
            return row
    raise AssertionError(f"missing run_id {run_id}")


def corridor_coverage(run: dict) -> float:
    seen = {event["corridor_slice"] for event in run["events"]}
    if not PLAN_SLICES:
        return 0.0
    return len(seen & PLAN_SLICES) / len(PLAN_SLICES)


def assert_single_epoch(run: dict) -> None:
    epochs = {event["ownership_epoch"] for event in run["events"]}
    assert len(epochs) == 1, f"expected one ownership epoch, saw {epochs}"


def assert_override_monotonic(run: dict) -> None:
    gens = [event["override_generation"] for event in run["events"]]
    for prev, cur in zip(gens, gens[1:]):
        assert cur >= prev, "override_generation decreased"


def assert_converged(run: dict) -> None:
    assert run["outcome"] == OUTCOME_CONVERGED


def converged_run_count(doc: dict) -> int:
    return sum(1 for row in doc["runs"] if row["outcome"] == OUTCOME_CONVERGED)


def test_epoch_convergence(trace_doc: dict) -> None:
    """Clean failover promotes one epoch with full corridor coverage."""
    run = run_by_id(trace_doc, "epoch_convergence")
    assert_converged(run)
    assert_single_epoch(run)
    assert_override_monotonic(run)
    assert corridor_coverage(run) == 1.0


def test_load_pulse(trace_doc: dict) -> None:
    """Concurrent emergency window keeps override generations monotonic when converged."""
    run = run_by_id(trace_doc, "load_pulse")
    assert_converged(run)
    assert_override_monotonic(run)


def test_lane_span(trace_doc: dict) -> None:
    """Multi-segment plan requires every corridor slice in converged runs."""
    run = run_by_id(trace_doc, "lane_span")
    assert_converged(run)
    assert corridor_coverage(run) == 1.0


def test_shadow_drop(trace_doc: dict) -> None:
    """Journal replay after promotion must not execute stale emergency generations."""
    run = run_by_id(trace_doc, "shadow_drop")
    assert_converged(run)
    for event in run["events"]:
        if event["override_generation"] <= BASELINE_OVERRIDE:
            raise AssertionError("stale emergency generation replayed")


def test_divergent_recovery(trace_doc: dict) -> None:
    """Corrupt-then-valid failover sequence converges without manual reset."""
    run = run_by_id(trace_doc, "divergent_recovery")
    assert_converged(run)
    assert corridor_coverage(run) == 1.0


def test_trace_continuity(trace_doc: dict) -> None:
    """Ledger chain head stays on the fixture baseline while behavior converges."""
    assert trace_doc["audit_chain_head"] == AUDIT_HEAD
    assert converged_run_count(trace_doc) >= 5


def test_delayed_commit(trace_doc: dict) -> None:
    """Actuator digests settle within two ticks without delayed_skew on converged runs."""
    run = run_by_id(trace_doc, "delayed_commit")
    assert_converged(run)
    assert run["outcome"] != OUTCOME_DELAYED_SKEW
    digests = [event["actuator_digest"] for event in run["events"]]
    assert len(set(digests)) >= 1
