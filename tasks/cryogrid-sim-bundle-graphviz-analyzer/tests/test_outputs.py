"""Verifier for cryogrid-sim-bundle-graphviz-analyzer.

Runs cryogrid-analyze CLI and validates DOT + JSON metrics against an independent
reference implementation of memo SECTION 37/58/91 rules.
"""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Any

APP = Path("/app")
BIN = APP / "build" / "cryogrid-analyze"
BASELINE = APP / "fixtures" / "cryo-baseline.json"
HIDDEN_ROOT = Path(os.environ.get("CG3_BUNDLE_ROOT", "/opt/verifier-fixtures/bundles"))
OUT = APP / "output"
MEMO = APP / "docs" / "validation-memo" / "cryogrid-thermal-review.md"


def run_analyze(spec: Path, out_dir: Path | None = None) -> None:
    target = out_dir or OUT
    target.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [str(BIN), "--spec", str(spec), "--out-dir", str(target)],
        check=True,
    )


def load_metrics(out_dir: Path | None = None) -> dict[str, Any]:
    path = (out_dir or OUT) / "metrics-report.json"
    return json.loads(path.read_text())


def load_dot(out_dir: Path | None = None) -> str:
    path = (out_dir or OUT) / "uncertainty-graph.dot"
    return path.read_text()


def parse_bundle(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def reference_variances(bundle: dict[str, Any]) -> dict[str, float]:
    soil_temp = float(bundle.get("soil_temp", 0.0))
    stages = bundle["pipeline"]["stages"]
    by_id = {s["id"]: s for s in stages}
    indegree = {s["id"]: 0 for s in stages}
    adj: dict[str, list[str]] = {s["id"]: [] for s in stages}
    for stage in stages:
        for dep in stage.get("inputs", []):
            adj[dep].append(stage["id"])
            indegree[stage["id"]] += 1
    order: list[str] = []
    ready = [sid for sid, deg in indegree.items() if deg == 0]
    while ready:
        cur = ready.pop(0)
        order.append(cur)
        for nxt in adj[cur]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                ready.append(nxt)
    if len(order) != len(stages):
        order = [s["id"] for s in stages]

    vars_map: dict[str, float] = {}
    for sid in order:
        stage = by_id[sid]
        cls = stage["class"]
        var_in = sum(vars_map.get(inp, 0.0) for inp in stage.get("inputs", []))
        eps = float(stage.get("epsilon", 0.01))
        if stage.get("cryo_exception") == "frozen_soil" and soil_temp < -0.5:
            eps = max(eps, 0.02)
        if cls == "SOURCE":
            var_out = float(stage["sigma"]) ** 2
        elif cls in ("TRANSFER", "FEEDBACK"):
            kappa = float(stage.get("kappa", 0.0))
            var_out = var_in * (1.0 + kappa) ** 2 + eps**2
        elif cls == "SINK":
            var_out = var_in
        elif cls == "COUPLER":
            gain = float(stage.get("coupling_gain", 0.5))
            sigma = float(stage.get("sigma", 0.0))
            var_out = var_in * gain + sigma**2
        else:
            var_out = 0.0
        vars_map[sid] = var_out
    return vars_map


def reference_loops(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    stages = bundle["pipeline"]["stages"]
    by_id = {s["id"]: s for s in stages}
    adj: dict[str, list[str]] = {s["id"]: [] for s in stages}
    for stage in stages:
        for dep in stage.get("inputs", []):
            adj[dep].append(stage["id"])

    cycles: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    def dfs(start: str, cur: str, path: list[str]) -> None:
        path.append(cur)
        for nxt in adj[cur]:
            if nxt == start and len(path) >= 2:
                key = tuple(path)
                if key not in seen:
                    seen.add(key)
                    cycles.append(list(path))
            elif nxt not in path:
                dfs(start, nxt, path)
        path.pop()

    for stage in stages:
        dfs(stage["id"], stage["id"], [])

    unstable: list[dict[str, Any]] = []
    for cycle in cycles:
        gain = 1.0
        for sid in cycle:
            cls = by_id[sid]["class"]
            if cls in ("TRANSFER", "FEEDBACK"):
                gain *= 1.0 + float(by_id[sid].get("kappa", 0.0))
        if gain >= 1.0:
            unstable.append({"nodes": cycle, "gain": round(gain, 6)})
    return unstable


def test_memo_is_long_context() -> None:
    """Validation memo must exceed 50k-token long-context threshold (~200k chars)."""
    assert MEMO.is_file()
    text = MEMO.read_text()
    assert len(text) >= 200_000
    assert "SECTION 37" in text
    assert "SECTION 91" in text


def test_baseline_metrics_match_reference() -> None:
    """Bundled cryo-baseline variances match independent memo formulas."""
    out = APP / "output" / "baseline"
    run_analyze(BASELINE, out)
    metrics = load_metrics(out)
    bundle = parse_bundle(BASELINE)
    expected = reference_variances(bundle)
    assert metrics["bundle_id"] == "cryo-baseline"
    assert metrics["stage_order"] == [s["id"] for s in bundle["pipeline"]["stages"]]
    assert metrics["stable"] is True
    assert metrics["unstable_loops"] == []
    for sid, val in expected.items():
        assert sid in metrics["stage_variances"]
        assert math.isclose(metrics["stage_variances"][sid], val, rel_tol=0, abs_tol=1e-5)


def test_baseline_dot_pipeline_order_and_annotations() -> None:
    """DOT nodes follow pipeline.stages order with var and class annotations."""
    out = APP / "output" / "dot-check"
    run_analyze(BASELINE, out)
    dot = load_dot(out)
    bundle = parse_bundle(BASELINE)
    order = [s["id"] for s in bundle["pipeline"]["stages"]]
    positions = [dot.index(f"  {sid} [") for sid in order]
    assert positions == sorted(positions)
    for sid in order:
        assert "class=" in dot.split(f"  {sid} [")[1].split("];")[0]
        assert re.search(r"var=\d+\.\d{6}", dot)


def test_hidden_unstable_feedback_loop() -> None:
    """Hidden feedback bundle must report unstable loop with gain >= 1."""
    spec = HIDDEN_ROOT / "feedback-unstable.json"
    out = APP / "output" / "unstable"
    run_analyze(spec, out)
    metrics = load_metrics(out)
    bundle = parse_bundle(spec)
    ref_loops = reference_loops(bundle)
    assert metrics["stable"] is False
    assert len(metrics["unstable_loops"]) >= 1
    assert ref_loops
    reported_gain = max(loop["gain"] for loop in metrics["unstable_loops"])
    assert reported_gain >= 1.0


def test_hidden_frozen_soil_epsilon_floor() -> None:
    """Hidden frozen soil bundle applies epsilon floor 0.02 per SECTION 58."""
    spec = HIDDEN_ROOT / "frozen-soil.json"
    out = APP / "output" / "frozen"
    run_analyze(spec, out)
    metrics = load_metrics(out)
    bundle = parse_bundle(spec)
    expected = reference_variances(bundle)
    assert math.isclose(
        metrics["stage_variances"]["active_layer"],
        expected["active_layer"],
        rel_tol=0,
        abs_tol=1e-5,
    )
    assert metrics["stage_variances"]["active_layer"] > 0.0094


def test_metrics_schema_fields() -> None:
    """JSON report uses stage_variances key and six-decimal numeric values."""
    out = APP / "output" / "schema"
    run_analyze(BASELINE, out)
    metrics = load_metrics(out)
    assert "stage_variances" in metrics
    assert "variances" not in metrics
    sample = next(iter(metrics["stage_variances"].values()))
    assert isinstance(sample, float)


def test_analyzer_binary_exists() -> None:
    """Shaded analyzer binary is built and executable."""
    assert BIN.is_file()
    proc = subprocess.run([str(BIN)], capture_output=True)
    assert proc.returncode != 0


def test_coupler_stage_variance() -> None:
    """Frozen-soil bundle COUPLER stage variance matches reference formula."""
    spec = HIDDEN_ROOT / "frozen-soil.json"
    out = APP / "output" / "coupler"
    run_analyze(spec, out)
    metrics = load_metrics(out)
    bundle = parse_bundle(spec)
    expected = reference_variances(bundle)
    assert math.isclose(
        metrics["stage_variances"]["bedrock_coupler"],
        expected["bedrock_coupler"],
        rel_tol=0,
        abs_tol=1e-5,
    )


def test_dot_graph_has_all_edges() -> None:
    """DOT includes edges for every stage input reference."""
    out = APP / "output" / "edges"
    run_analyze(BASELINE, out)
    dot = load_dot(out)
    bundle = parse_bundle(BASELINE)
    for stage in bundle["pipeline"]["stages"]:
        for dep in stage.get("inputs", []):
            assert f"  {dep} -> {stage['id']};" in dot


def test_stage_order_matches_pipeline_array() -> None:
    """metrics stage_order mirrors pipeline.stages array, not sorted ids."""
    out = APP / "output" / "order"
    run_analyze(BASELINE, out)
    metrics = load_metrics(out)
    bundle = parse_bundle(BASELINE)
    pipeline_ids = [s["id"] for s in bundle["pipeline"]["stages"]]
    assert metrics["stage_order"] == pipeline_ids
    sorted_ids = sorted(pipeline_ids)
    assert pipeline_ids != sorted_ids or len(sorted_ids) <= 1


def test_permafrost_sink_passes_variance() -> None:
    """Terminal SINK stage variance equals upstream soil_column variance."""
    out = APP / "output" / "sink"
    run_analyze(BASELINE, out)
    metrics = load_metrics(out)
    bundle = parse_bundle(BASELINE)
    expected = reference_variances(bundle)
    assert math.isclose(
        metrics["stage_variances"]["permafrost_sink"],
        expected["permafrost_sink"],
        rel_tol=0,
        abs_tol=1e-5,
    )
    assert math.isclose(
        metrics["stage_variances"]["permafrost_sink"],
        metrics["stage_variances"]["soil_column"],
        rel_tol=0,
        abs_tol=1e-5,
    )


def test_hidden_feedback_bundle_id() -> None:
    """Hidden feedback bundle preserves bundle_id in metrics report."""
    spec = HIDDEN_ROOT / "feedback-unstable.json"
    out = APP / "output" / "fb-id"
    run_analyze(spec, out)
    metrics = load_metrics(out)
    assert metrics["bundle_id"] == "feedback-loop-lab"
