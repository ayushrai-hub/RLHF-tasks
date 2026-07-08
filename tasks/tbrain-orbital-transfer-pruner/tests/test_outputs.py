import json
import subprocess
from pathlib import Path


def run_pruner(tmp_path: Path, scenario: dict) -> dict:
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")
    result = subprocess.run(
        ["node", "/app/bin/transfer-pruner.js", str(scenario_path)],
        cwd="/app",
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    return json.loads(result.stdout)


def test_gravity_assist_label_survives_single_metric_pruning(tmp_path: Path) -> None:
    """A slower token-bearing route should remain when it enables a low-dv assist."""
    scenario = {
        "origin": "Earth",
        "epoch": 0,
        "targets": ["Jupiter"],
        "arcs": [
            {"from": "Earth", "to": "Relay", "depart": 0, "duration": 1, "dv": 2, "dose": 0},
            {"from": "Relay", "to": "Jupiter", "depart": 2, "period": 3, "duration": 1, "dv": 8, "dose": 2},
            {"from": "Earth", "to": "Luna", "depart": 1, "duration": 3, "dv": 4, "dose": 1, "grants": ["lunar"]},
            {"from": "Luna", "to": "Jupiter", "depart": 6, "period": 5, "duration": 2, "dv": 1, "dose": 1, "requires": ["lunar"]},
        ],
    }
    assert run_pruner(tmp_path, scenario)["frontier"] == [
        {"target": "Jupiter", "arrival": 8, "dv": 5, "dose": 2, "path": ["Earth", "Luna", "Jupiter"]},
        {"target": "Jupiter", "arrival": 3, "dv": 10, "dose": 2, "path": ["Earth", "Relay", "Jupiter"]},
    ]


def test_periodic_launch_window_rolls_forward_from_arrival(tmp_path: Path) -> None:
    """Periodic windows should use the first valid future departure, not the base epoch."""
    scenario = {
        "origin": "A",
        "epoch": 5,
        "targets": ["B"],
        "arcs": [
            {"from": "A", "to": "B", "depart": 1, "period": 4, "duration": 2, "dv": 3, "dose": 0},
        ],
    }
    assert run_pruner(tmp_path, scenario)["frontier"] == [
        {"target": "B", "arrival": 7, "dv": 3, "dose": 0, "path": ["A", "B"]},
    ]


def test_token_superset_may_dominate_equal_metrics_but_subset_cannot(tmp_path: Path) -> None:
    """Dominance at an intermediate body must consider resource token containment."""
    scenario = {
        "origin": "Start",
        "epoch": 0,
        "targets": ["Outpost"],
        "arcs": [
            {"from": "Start", "to": "Hub", "depart": 0, "duration": 2, "dv": 3, "dose": 0},
            {"from": "Start", "to": "Hub", "depart": 0, "duration": 2, "dv": 3, "dose": 0, "grants": ["ice"]},
            {"from": "Hub", "to": "Outpost", "depart": 3, "duration": 1, "dv": 1, "dose": 0, "requires": ["ice"]},
            {"from": "Hub", "to": "Outpost", "depart": 3, "duration": 1, "dv": 6, "dose": 0},
        ],
    }
    assert run_pruner(tmp_path, scenario)["frontier"] == [
        {"target": "Outpost", "arrival": 4, "dv": 4, "dose": 0, "path": ["Start", "Hub", "Outpost"]},
    ]


def test_equal_cost_distinct_paths_are_not_collapsed(tmp_path: Path) -> None:
    """A tie on all numeric dimensions is not dominance when the paths differ."""
    scenario = {
        "origin": "Earth",
        "epoch": 0,
        "targets": ["Probe"],
        "arcs": [
            {"from": "Earth", "to": "Aster", "depart": 0, "duration": 1, "dv": 1, "dose": 0},
            {"from": "Aster", "to": "Probe", "depart": 1, "duration": 1, "dv": 2, "dose": 1},
            {"from": "Earth", "to": "Beacon", "depart": 0, "duration": 1, "dv": 1, "dose": 0},
            {"from": "Beacon", "to": "Probe", "depart": 1, "duration": 1, "dv": 2, "dose": 1},
        ],
    }
    assert run_pruner(tmp_path, scenario)["frontier"] == [
        {"target": "Probe", "arrival": 2, "dv": 3, "dose": 1, "path": ["Earth", "Aster", "Probe"]},
        {"target": "Probe", "arrival": 2, "dv": 3, "dose": 1, "path": ["Earth", "Beacon", "Probe"]},
    ]


def test_consumed_token_cannot_unlock_a_later_assist(tmp_path: Path) -> None:
    """A token consumed by one burn is no longer available for a later required assist."""
    scenario = {
        "origin": "Earth",
        "epoch": 0,
        "targets": ["Jupiter"],
        "arcs": [
            {"from": "Earth", "to": "Depot", "depart": 0, "duration": 1, "dv": 1, "dose": 0, "grants": ["voucher"]},
            {"from": "Depot", "to": "Mars", "depart": 1, "duration": 1, "dv": 1, "dose": 0, "requires": ["voucher"], "consumes": ["voucher"]},
            {"from": "Mars", "to": "Jupiter", "depart": 2, "duration": 1, "dv": 1, "dose": 0, "requires": ["voucher"]},
            {"from": "Depot", "to": "Jupiter", "depart": 4, "duration": 1, "dv": 6, "dose": 0},
        ],
    }
    assert run_pruner(tmp_path, scenario)["frontier"] == [
        {"target": "Jupiter", "arrival": 5, "dv": 7, "dose": 0, "path": ["Earth", "Depot", "Jupiter"]},
    ]


def test_token_inventory_after_consumption_affects_intermediate_dominance(tmp_path: Path) -> None:
    """Equal-metric labels are distinct when only one still carries the token needed downstream."""
    scenario = {
        "origin": "Start",
        "epoch": 0,
        "targets": ["Goal"],
        "arcs": [
            {"from": "Start", "to": "Hub", "depart": 0, "duration": 1, "dv": 2, "dose": 0, "grants": ["permit"]},
            {"from": "Start", "to": "Cache", "depart": 0, "duration": 1, "dv": 1, "dose": 0, "grants": ["permit"]},
            {"from": "Cache", "to": "Hub", "depart": 1, "duration": 0, "dv": 1, "dose": 0, "consumes": ["permit"]},
            {"from": "Hub", "to": "Goal", "depart": 2, "duration": 1, "dv": 1, "dose": 0, "requires": ["permit"]},
            {"from": "Hub", "to": "Goal", "depart": 2, "duration": 1, "dv": 5, "dose": 0},
        ],
    }
    assert run_pruner(tmp_path, scenario)["frontier"] == [
        {"target": "Goal", "arrival": 3, "dv": 3, "dose": 0, "path": ["Start", "Hub", "Goal"]},
    ]


def test_target_constraints_filter_after_frontier_search(tmp_path: Path) -> None:
    """Per-target cost caps should remove otherwise non-dominated high-dose arrivals."""
    scenario = {
        "origin": "Earth",
        "epoch": 0,
        "targets": ["Europa"],
        "targetConstraints": {"Europa": {"maxDose": 2, "maxArrival": 9}},
        "arcs": [
            {"from": "Earth", "to": "Europa", "depart": 0, "duration": 4, "dv": 2, "dose": 5},
            {"from": "Earth", "to": "Venus", "depart": 0, "duration": 2, "dv": 3, "dose": 1},
            {"from": "Venus", "to": "Europa", "depart": 5, "period": 2, "duration": 2, "dv": 2, "dose": 1},
            {"from": "Earth", "to": "Slow", "depart": 0, "duration": 8, "dv": 1, "dose": 0},
            {"from": "Slow", "to": "Europa", "depart": 10, "duration": 1, "dv": 1, "dose": 0},
        ],
    }
    assert run_pruner(tmp_path, scenario)["frontier"] == [
        {"target": "Europa", "arrival": 7, "dv": 5, "dose": 2, "path": ["Earth", "Venus", "Europa"]},
    ]


def test_target_required_token_must_remain_unconsumed_at_arrival(tmp_path: Path) -> None:
    """A target token requirement checks final inventory, not only whether the token appeared earlier."""
    scenario = {
        "origin": "Earth",
        "epoch": 0,
        "targets": ["Lab"],
        "targetConstraints": {"Lab": {"requires": ["sample"], "maxDv": 8}},
        "arcs": [
            {"from": "Earth", "to": "Moon", "depart": 0, "duration": 1, "dv": 1, "dose": 0, "grants": ["sample"]},
            {"from": "Moon", "to": "Lab", "depart": 1, "duration": 1, "dv": 1, "dose": 0, "consumes": ["sample"]},
            {"from": "Moon", "to": "Safe", "depart": 2, "duration": 1, "dv": 3, "dose": 0},
            {"from": "Safe", "to": "Lab", "depart": 3, "duration": 1, "dv": 1, "dose": 0},
        ],
    }
    assert run_pruner(tmp_path, scenario)["frontier"] == [
        {"target": "Lab", "arrival": 4, "dv": 5, "dose": 0, "path": ["Earth", "Moon", "Safe", "Lab"]},
    ]


def test_forbidden_arc_keeps_clean_label_from_token_superset_pruning(tmp_path: Path) -> None:
    """Extra tokens can be harmful, so a clean equal-cost label must survive pruning."""
    scenario = {
        "origin": "Start",
        "epoch": 0,
        "targets": ["Lab"],
        "arcs": [
            {"from": "Start", "to": "Hub", "depart": 0, "duration": 1, "dv": 1, "dose": 0},
            {"from": "Start", "to": "Cache", "depart": 0, "duration": 1, "dv": 1, "dose": 0, "grants": ["contam"]},
            {"from": "Cache", "to": "Hub", "depart": 1, "duration": 0, "dv": 0, "dose": 0},
            {"from": "Hub", "to": "Lab", "depart": 1, "duration": 1, "dv": 1, "dose": 0, "forbids": ["contam"]},
            {"from": "Hub", "to": "Lab", "depart": 1, "duration": 1, "dv": 5, "dose": 0},
        ],
    }
    assert run_pruner(tmp_path, scenario)["frontier"] == [
        {"target": "Lab", "arrival": 2, "dv": 2, "dose": 0, "path": ["Start", "Hub", "Lab"]},
    ]


def test_target_forbids_filter_final_token_inventory_after_search(tmp_path: Path) -> None:
    """Target constraints can reject a faster path whose final inventory still has a forbidden token."""
    scenario = {
        "origin": "Earth",
        "epoch": 0,
        "targets": ["Lab"],
        "targetConstraints": {"Lab": {"forbids": ["contam"]}},
        "arcs": [
            {"from": "Earth", "to": "Moon", "depart": 0, "duration": 1, "dv": 1, "dose": 0, "grants": ["contam"]},
            {"from": "Moon", "to": "Lab", "depart": 1, "duration": 1, "dv": 1, "dose": 0},
            {"from": "Earth", "to": "Clean", "depart": 0, "duration": 2, "dv": 3, "dose": 0},
            {"from": "Clean", "to": "Lab", "depart": 2, "duration": 1, "dv": 2, "dose": 0},
        ],
    }
    assert run_pruner(tmp_path, scenario)["frontier"] == [
        {"target": "Lab", "arrival": 3, "dv": 5, "dose": 0, "path": ["Earth", "Clean", "Lab"]},
    ]


def test_consumes_before_grants_can_refresh_a_target_token(tmp_path: Path) -> None:
    """A leg that consumes and grants the same token should refresh it for the final target."""
    scenario = {
        "origin": "Earth",
        "epoch": 0,
        "targets": ["Lab"],
        "targetConstraints": {"Lab": {"requires": ["permit"]}},
        "arcs": [
            {"from": "Earth", "to": "Depot", "depart": 0, "duration": 1, "dv": 1, "dose": 0, "grants": ["permit"]},
            {"from": "Depot", "to": "Lab", "depart": 1, "duration": 1, "dv": 1, "dose": 0, "requires": ["permit"], "consumes": ["permit"], "grants": ["permit"]},
        ],
    }
    assert run_pruner(tmp_path, scenario)["frontier"] == [
        {"target": "Lab", "arrival": 2, "dv": 2, "dose": 0, "path": ["Earth", "Depot", "Lab"]},
    ]
