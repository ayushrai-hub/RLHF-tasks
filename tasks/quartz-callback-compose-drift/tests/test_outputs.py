"""Verifier for quartz-callback-compose-drift."""

import contextlib
import csv
import json
import math
import os
import subprocess
from pathlib import Path

import pytest

APP = Path("/app")
HARNESS = APP / "bin" / "ode_harness"
PROBE = APP / "bin" / "ode_probe"
PLAN = APP / "data" / "ode_plan.tbl"
HOOKS = APP / "data" / "hooks.tbl"
OVERLAY = APP / "cfg" / "ode_overlay.toml"
SUMMARY = APP / "output" / "run_summary.json"
TRACE = APP / "output" / "trace.csv"


def _overlay():
    vals = {"tol": 1e-6, "metric_scale": 1.0, "restart_target": 1.0, "carry_gain": 0.005}
    for line in OVERLAY.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            vals[k.strip()] = float(v.strip())
    return vals


def _effective_scale(overlay, prev_event_step):
    carry = 0.0 if prev_event_step < 0 else overlay["carry_gain"] * prev_event_step
    return overlay["metric_scale"] * (1.0 + carry)


def _read_plan():
    rows = []
    for line in PLAN.read_text().splitlines()[1:]:
        if not line.strip():
            continue
        tag, y0, dt, steps, callback_order, restart_step = line.split("|")
        rows.append(
            {
                "tag": tag,
                "y0": float(y0),
                "dt": float(dt),
                "steps": int(steps),
                "callback_order": callback_order,
                "restart_step": int(restart_step),
            }
        )
    return rows


def _read_hooks():
    hooks = {}
    for line in HOOKS.read_text().splitlines()[1:]:
        if not line.strip():
            continue
        name, threshold, on_fire = line.split("|")
        effect = None
        if on_fire.startswith("add:"):
            effect = ("add", float(on_fire[4:]))
        elif on_fire.startswith("mul:"):
            effect = ("mul", float(on_fire[4:]))
        elif on_fire.startswith("set:"):
            effect = ("set", float(on_fire[4:]))
        hooks[name] = {"threshold": float(threshold), "on_fire": effect}
    return hooks


def _plan_header():
    return PLAN.read_text().splitlines()[0]


def _hooks_header():
    return HOOKS.read_text().splitlines()[0]


def _plan_row(tag, y0, dt, steps, callback_order, restart_step):
    return f"{tag}|{y0}|{dt}|{steps}|{callback_order}|{restart_step}"


def _hook_row(name, threshold, on_fire):
    return f"{name}|{threshold}|{on_fire}"


_DYN_SEQ = 0x71A5


def _fresh_nonce():
    global _DYN_SEQ
    _DYN_SEQ += 1
    return format(_DYN_SEQ, "x")


def _parse_callbacks(order):
    out = []
    for idx, part in enumerate(p for p in order.split(";") if p):
        name, lo = part.split(":")
        out.append({"name": name, "load_order": int(lo), "registration": idx})
    return out


def _order_sensitive(callbacks):
    seen = set()
    for cb in callbacks:
        if cb["load_order"] in seen:
            return True
        seen.add(cb["load_order"])
    return False


def _hook_fires(y_prev, y_curr, threshold, step, y0):
    if step == 0:
        return y0 >= threshold
    return y_prev < threshold <= y_curr


def _apply_effect(y, effect):
    if effect is None:
        return y
    kind, val = effect
    if kind == "add":
        return y + val
    if kind == "mul":
        return y * val
    return val


def _model_case(row, hooks, overlay, prev_event_step=-1):
    callbacks = _parse_callbacks(row["callback_order"])
    order = sorted(callbacks, key=lambda c: (c["load_order"], c["registration"]))
    y = row["y0"]
    event_step = None
    metric = 0.0
    scale = _effective_scale(overlay, prev_event_step)
    tol = overlay["tol"]
    restart_target = overlay["restart_target"]
    for step in range(row["steps"]):
        y_prev = y
        y = y - row["dt"] * y
        if row["restart_step"] >= 0 and step == row["restart_step"] and y < tol:
            y = restart_target
        for cb in order:
            hook = hooks[cb["name"]]
            if _hook_fires(y_prev, y, hook["threshold"], step, row["y0"]):
                if event_step is None:
                    event_step = step
                y = _apply_effect(y, hook["on_fire"])
        metric += scale * row["dt"] * (y_prev + y) / 2.0
    return {
        "tag": row["tag"],
        "event_step": -1 if event_step is None else event_step,
        "metric_integral": metric,
        "order_sensitive": _order_sensitive(callbacks),
    }


def _chain_model(y_prev, y_post, step, y0, order, hooks, restart_applied, restart_y):
    callbacks = _parse_callbacks(order)
    sorted_cbs = sorted(callbacks, key=lambda c: (c["load_order"], c["registration"]))
    y = y_post
    if restart_applied:
        y = restart_y
    for cb in sorted_cbs:
        hook = hooks[cb["name"]]
        if _hook_fires(y_prev, y, hook["threshold"], step, y0):
            y = _apply_effect(y, hook["on_fire"])
    return y


def _model(overlay=None, plan_rows=None, hooks_map=None):
    if overlay is None:
        overlay = _overlay()
    if hooks_map is None:
        hooks_map = _read_hooks()
    if plan_rows is None:
        plan_rows = _read_plan()
    prev_es = -1
    out = []
    for row in plan_rows:
        case = _model_case(row, hooks_map, overlay, prev_es)
        prev_es = case["event_step"]
        out.append(case)
    return out


def _parse_plan_text(text):
    rows = []
    for line in text.splitlines()[1:]:
        if not line.strip():
            continue
        tag, y0, dt, steps, callback_order, restart_step = line.split("|")
        rows.append(
            {
                "tag": tag,
                "y0": float(y0),
                "dt": float(dt),
                "steps": int(steps),
                "callback_order": callback_order,
                "restart_step": int(restart_step),
            }
        )
    return rows


def _parse_hooks_text(text):
    hooks = {}
    for line in text.splitlines()[1:]:
        if not line.strip():
            continue
        name, threshold, on_fire = line.split("|")
        effect = None
        if on_fire.startswith("add:"):
            effect = ("add", float(on_fire[4:]))
        elif on_fire.startswith("mul:"):
            effect = ("mul", float(on_fire[4:]))
        elif on_fire.startswith("set:"):
            effect = ("set", float(on_fire[4:]))
        hooks[name] = {"threshold": float(threshold), "on_fire": effect}
    return hooks


def _rebuild_locked():
    subprocess.run(
        [
            "cargo",
            "build",
            "--release",
            "--locked",
            "--bins",
            "--manifest-path",
            "/app/environment/Cargo.toml",
        ],
        check=True,
    )


@contextlib.contextmanager
def _swap_inputs(plan_text, hooks_text):
    plan_backup = PLAN.read_text()
    hooks_backup = HOOKS.read_text()
    PLAN.write_text(plan_text if plan_text.endswith("\n") else plan_text + "\n")
    HOOKS.write_text(hooks_text if hooks_text.endswith("\n") else hooks_text + "\n")
    try:
        yield
    finally:
        PLAN.write_text(plan_backup)
        HOOKS.write_text(hooks_backup)
        _rebuild_locked()
        _run_harness()


def _expected_digest(cases):
    return "|".join(
        f"{c['tag']}:{c['event_step']}:{c['metric_integral']:.6f}" for c in cases
    )


def _analytic_decay_integral(y0, dt, steps):
    t_end = dt * steps
    return y0 * (1.0 - math.exp(-t_end))


def _probe(env):
    proc = subprocess.run(
        [PROBE],
        cwd=APP,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def _set_overlay(**kwargs):
    lines = []
    for line in OVERLAY.read_text().splitlines():
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            if key in kwargs:
                lines.append(f"{key}={kwargs[key]}")
                continue
        lines.append(line)
    for key, val in kwargs.items():
        if not any(line.startswith(f"{key}=") for line in lines):
            lines.append(f"{key}={val}")
    OVERLAY.write_text("\n".join(lines) + "\n")


def _run_harness():
    subprocess.run([HARNESS], cwd=APP, check=True)


def _load_summary():
    return json.loads(SUMMARY.read_text())


def _cases_by_tag():
    return {c["tag"]: c for c in _load_summary()["cases"]}


@pytest.fixture(scope="module", autouse=True)
def _build():
    _rebuild_locked()
    _run_harness()


def test_pipeline_matches_independent_model():
    """Full pipeline: every case must match the independent Python integrator."""
    exp = {c["tag"]: c for c in _model()}
    got = _load_summary()
    assert got["schema_version"] == "run.v1"
    for case in got["cases"]:
        e = exp[case["tag"]]
        assert case["event_step"] == e["event_step"]
        assert abs(case["metric_integral"] - e["metric_integral"]) < 1e-6
        assert case["order_sensitive"] == e["order_sensitive"]


def test_pipeline_summary_flags_coherent():
    """Full pipeline: per-case ok flags must be true when outputs match the model."""
    exp = {c["tag"]: c for c in _model()}
    for case in _load_summary()["cases"]:
        e = exp[case["tag"]]
        aligned = (
            case["event_step"] == e["event_step"]
            and abs(case["metric_integral"] - e["metric_integral"]) < 1e-6
        )
        if aligned:
            assert case["euler_ok"] is True
            assert case["event_ok"] is True
            assert case["metric_ok"] is True
            assert case["summary_ok"] is True


def test_pipeline_restart_pulse_cross_module():
    """Restart timing, hook crossing, and metric must align for restart_pulse."""
    exp = next(c for c in _model() if c["tag"] == "restart_pulse")
    got = _cases_by_tag()["restart_pulse"]
    assert got["event_step"] == exp["event_step"]
    assert got["restart_ok"] is True
    assert got["summary_ok"] is True


def test_trace_json_cross_artifact():
    """Trace CSV must mirror JSON run summary fields per tag."""
    audit = _load_summary()
    with TRACE.open() as f:
        rows = {r["tag"]: r for r in csv.DictReader(f)}
    for case in audit["cases"]:
        row = rows[case["tag"]]
        assert int(row["event_step"]) == case["event_step"]
        assert float(row["metric_integral"]) == pytest.approx(case["metric_integral"], rel=0, abs=1e-6)
        assert row["report_line"] == case["report_line"]
        assert row["summary_ok"].lower() == str(case["summary_ok"]).lower()


def test_digest_trace_cross_artifact():
    """Digest must match an independent hash over case metrics."""
    audit = _load_summary()
    expected = _expected_digest(audit["cases"])
    assert audit["digest"] == expected


def test_independent_analytic_decay_bound():
    """Decay integral metric must sit below the closed-form exp decay integral."""
    row = next(r for r in _read_plan() if r["tag"] == "decay_integral")
    analytic = _analytic_decay_integral(row["y0"], row["dt"], row["steps"])
    model = next(c for c in _model() if c["tag"] == "decay_integral")
    assert model["metric_integral"] < analytic
    got = _cases_by_tag()["decay_integral"]
    assert got["metric_integral"] == pytest.approx(model["metric_integral"], rel=0, abs=1e-6)


def test_probe_euler_secondary():
    """Euler probe must subtract dt*y for the decay model."""
    assert float(_probe({"TB_PROBE": "euler", "TB_Y": "2.0", "TB_DT": "0.1"})) == pytest.approx(1.8)


def test_probe_event_step0_and_boundary():
    """Event probe must use y0 at step zero and inclusive upper threshold."""
    assert _probe(
        {
            "TB_PROBE": "event",
            "TB_PREV": "0.4",
            "TB_CURR": "0.49",
            "TB_THRESH": "0.5",
            "TB_STEP": "1",
            "TB_Y0": "0.4",
        }
    ) == "0"
    assert _probe(
        {
            "TB_PROBE": "event",
            "TB_PREV": "0.4",
            "TB_CURR": "0.5",
            "TB_THRESH": "0.5",
            "TB_STEP": "1",
            "TB_Y0": "0.4",
        }
    ) == "1"
    assert _probe(
        {
            "TB_PROBE": "event",
            "TB_PREV": "0.51",
            "TB_CURR": "0.49",
            "TB_THRESH": "0.5",
            "TB_STEP": "0",
            "TB_Y0": "0.52",
        }
    ) == "1"


def test_probe_sort_tiebreak_secondary():
    """Sort probe must order by load order then registration tiebreak."""
    assert _probe({"TB_PROBE": "sort", "TB_ORDER": "reclaim:1;mark:1"}) == "reclaim,mark"
    assert _probe({"TB_PROBE": "sort", "TB_ORDER": "mark:1;reclaim:1"}) == "mark,reclaim"


def test_probe_restart_and_metric_overlay():
    """Restart and metric probes must honor overlay target and scale."""
    assert float(
        _probe(
            {
                "TB_PROBE": "restart",
                "TB_Y": "1e-9",
                "TB_Y0": "0.35",
                "TB_TOL": "1e-6",
                "TB_TARGET": "1.0",
            }
        )
    ) == pytest.approx(1.0)
    assert float(
        _probe(
            {
                "TB_PROBE": "metric",
                "TB_Y_PREV": "1.0",
                "TB_Y_CURR": "0.9",
                "TB_DT": "0.1",
                "TB_SCALE": "2.0",
            }
        )
    ) == pytest.approx(0.19)


def test_probe_summary_requires_all_checks():
    """Summary probe must require all sub-checks, not partial matches."""
    assert _probe(
        {
            "TB_PROBE": "summary",
            "TB_EULER_OK": "1",
            "TB_EVENT_OK": "0",
            "TB_RESTART_OK": "1",
            "TB_METRIC_OK": "1",
        }
    ) == "drift"
    assert _probe(
        {
            "TB_PROBE": "summary",
            "TB_EULER_OK": "1",
            "TB_EVENT_OK": "1",
            "TB_RESTART_OK": "1",
            "TB_METRIC_OK": "1",
        }
    ) == "ok"


def test_step0_y0_only_requires_y0_not_post_euler():
    """step0_y0_only fires from y0 even when post-Euler y is below threshold."""
    got = _cases_by_tag()
    exp = next(c for c in _model() if c["tag"] == "step0_y0_only")
    assert got["step0_y0_only"]["event_step"] == exp["event_step"]
    assert got["step0_y0_only"]["event_step"] == 0


def test_order_sensitive_tie_flip_interaction():
    """Swapped tied registration must change metric via sort+tiebreak interaction."""
    got = _cases_by_tag()
    assert got["order_sensitive"]["order_sensitive"] is True
    assert got["order_sensitive"]["metric_integral"] != got["tie_flip"]["metric_integral"]


def test_near_miss_strict_gt_event_fails_pipeline():
    """Strict-greater threshold at equality must not count as a crossing in late_cross."""
    got = _cases_by_tag()
    exp = next(c for c in _model() if c["tag"] == "late_cross")
    assert got["late_cross"]["event_step"] == exp["event_step"]
    assert got["late_cross"]["event_step"] == 0


def test_near_miss_or_summary_flags_fail():
    """Partial sub-check success must not yield summary_ok or report_line ok."""
    for case in _load_summary()["cases"]:
        flags = [case["euler_ok"], case["event_ok"], case["restart_ok"], case["metric_ok"]]
        if not all(flags):
            assert case["summary_ok"] is False
            assert case["report_line"] == "drift"


def test_mutation_tol_changes_restart_pulse_only():
    """Tightening tol must change restart_pulse without altering decay_integral."""
    baseline = _cases_by_tag()
    prior_tol = _overlay()["tol"]
    _set_overlay(tol=prior_tol / 10.0)
    try:
        _run_harness()
        got = _cases_by_tag()
        assert got["restart_pulse"]["event_step"] != baseline["restart_pulse"]["event_step"]
        assert got["decay_integral"]["metric_integral"] == pytest.approx(
            baseline["decay_integral"]["metric_integral"], rel=0, abs=1e-6
        )
    finally:
        _set_overlay(tol=prior_tol)
        _run_harness()


def test_mutation_metric_scale_changes_decay_only():
    """metric_scale mutation must rescale decay_integral but not order_sensitive."""
    baseline = _cases_by_tag()
    prior_scale = _overlay()["metric_scale"]
    mutated_scale = prior_scale + 1.0
    _set_overlay(metric_scale=mutated_scale)
    try:
        _run_harness()
        got = _cases_by_tag()
        assert got["decay_integral"]["metric_integral"] != baseline["decay_integral"]["metric_integral"]
        assert got["order_sensitive"]["event_step"] == baseline["order_sensitive"]["event_step"]
        overlay = {"tol": _overlay()["tol"], "metric_scale": mutated_scale, "restart_target": _overlay()["restart_target"], "carry_gain": _overlay()["carry_gain"]}
        exp = next(c for c in _model(overlay) if c["tag"] == "decay_integral")
        assert got["decay_integral"]["metric_integral"] == pytest.approx(exp["metric_integral"], rel=0, abs=1e-6)
    finally:
        _set_overlay(metric_scale=prior_scale)
        _run_harness()


def test_anti_static_plan_row_count():
    """Outputs must reflect the live plan row count, not a static fixture."""
    audit = _load_summary()
    assert len(audit["cases"]) == len(_read_plan())
    assert len(audit["cases"]) >= 11


def test_no_event_and_multi_order_pipeline():
    """no_event stays at -1; multi_order reaches summary_ok through three callbacks."""
    got = _cases_by_tag()
    assert got["no_event"]["event_step"] == -1
    assert got["multi_order"]["summary_ok"] is True
    assert got["multi_order"]["event_step"] == 0


def test_schema_json_exact_field_types_and_layout():
    """JSON summary must use exact field names, types, and nested case object layout."""
    audit = _load_summary()
    assert set(audit.keys()) == {"schema_version", "cases", "digest"}
    assert isinstance(audit["schema_version"], str)
    assert audit["schema_version"] == "run.v1"
    assert isinstance(audit["cases"], list)
    assert isinstance(audit["digest"], str)
    required = {
        "tag",
        "event_step",
        "metric_integral",
        "order_sensitive",
        "euler_ok",
        "event_ok",
        "restart_ok",
        "metric_ok",
        "summary_ok",
        "report_line",
    }
    for case in audit["cases"]:
        assert set(case.keys()) == required
        assert isinstance(case["tag"], str)
        assert isinstance(case["event_step"], int)
        assert isinstance(case["metric_integral"], (int, float))
        assert isinstance(case["order_sensitive"], bool)
        for flag in ("euler_ok", "event_ok", "restart_ok", "metric_ok", "summary_ok"):
            assert isinstance(case[flag], bool)
        assert isinstance(case["report_line"], str)
        assert case["report_line"] in ("ok", "drift")


def test_schema_digest_six_decimal_lowercase_tokens():
    """Digest tokens must use six decimal places for metric_integral in plan order."""
    audit = _load_summary()
    expected = _expected_digest(audit["cases"])
    assert audit["digest"] == expected
    for token in audit["digest"].split("|"):
        tag, event_step, metric = token.split(":")
        assert tag
        assert event_step.lstrip("-").isdigit()
        assert "." in metric
        frac = metric.split(".", 1)[1]
        assert len(frac) == 6
        assert metric == f"{float(metric):.6f}"


def test_schema_csv_column_order_and_boolean_spelling():
    """CSV trace must use exact column order with lowercase boolean strings."""
    header = TRACE.read_text().splitlines()[0]
    assert (
        header
        == "tag,event_step,metric_integral,order_sensitive,euler_ok,event_ok,restart_ok,metric_ok,summary_ok,report_line"
    )
    with TRACE.open() as f:
        rows = list(csv.DictReader(f))
    audit = _load_summary()
    assert [r["tag"] for r in rows] == [c["tag"] for c in audit["cases"]]
    for row, case in zip(rows, audit["cases"]):
        assert row["order_sensitive"] in ("true", "false")
        for col in ("euler_ok", "event_ok", "restart_ok", "metric_ok", "summary_ok"):
            assert row[col] in ("true", "false")
            assert row[col] == str(case[col]).lower()
        assert row["report_line"] in ("ok", "drift")


def test_schema_summary_ok_requires_all_subchecks_and():
    """summary_ok must be logical AND of euler, event, restart, and metric checks."""
    for case in _load_summary()["cases"]:
        expected = all(
            case[k] for k in ("euler_ok", "event_ok", "restart_ok", "metric_ok")
        )
        assert case["summary_ok"] == expected
        assert case["report_line"] == ("ok" if expected else "drift")


def test_semantic_overlay_restart_couples_event_digest_and_summary():
    """tol/restart_target overlay must couple restart_pulse event_step, digest, and summary_ok."""
    baseline_digest = _load_summary()["digest"]
    baseline_restart = _cases_by_tag()["restart_pulse"]
    prior_tol = _overlay()["tol"]
    prior_target = _overlay()["restart_target"]
    _set_overlay(tol=prior_tol / 100.0, restart_target=prior_target + 0.5)
    try:
        _run_harness()
        got = _cases_by_tag()
        overlay = _overlay()
        exp = next(c for c in _model(overlay) if c["tag"] == "restart_pulse")
        assert got["restart_pulse"]["event_step"] == exp["event_step"]
        assert got["restart_pulse"]["restart_ok"] is True
        assert got["restart_pulse"]["summary_ok"] is True
        assert _load_summary()["digest"] != baseline_digest
        if baseline_restart["event_step"] != exp["event_step"]:
            assert got["restart_pulse"]["event_step"] != baseline_restart["event_step"]
    finally:
        _set_overlay(tol=prior_tol, restart_target=prior_target)
        _run_harness()


def test_semantic_sort_tiebreak_couples_metric_event_and_digest():
    """Registration tiebreak must change metric_integral, event timing, and bundle digest."""
    got = _cases_by_tag()
    assert got["order_sensitive"]["order_sensitive"] is True
    assert got["tie_flip"]["order_sensitive"] is True
    assert got["order_sensitive"]["metric_integral"] != got["tie_flip"]["metric_integral"]
    exp_sensitive = next(c for c in _model() if c["tag"] == "order_sensitive")
    exp_flip = next(c for c in _model() if c["tag"] == "tie_flip")
    assert got["order_sensitive"]["event_step"] == exp_sensitive["event_step"]
    assert got["tie_flip"]["event_step"] == exp_flip["event_step"]
    tokens = {part.split(":", 1)[0]: part for part in _load_summary()["digest"].split("|")}
    assert tokens["order_sensitive"] != tokens["tie_flip"]


def test_rebuild_locked_binary_runs_not_stale_script():
    """Harness must be the freshly rebuilt release binary, not a hand-written script."""
    assert HARNESS.is_symlink() or HARNESS.is_file()
    assert not HARNESS.suffix == ".py"
    head = HARNESS.read_bytes()[:4]
    assert head != b"#!/b"
    _rebuild_locked()
    _run_harness()
    assert _load_summary()["schema_version"] == "run.v1"


def test_dynamic_variant_defeats_hardcoded_solution():
    """Fresh plan rows and hooks must produce correct outputs; static fixture hardcoding fails."""
    baseline_digest = _load_summary()["digest"]
    static_tags = {r["tag"] for r in _read_plan()}
    nonce = _fresh_nonce()
    tag_a = f"vf{nonce}a"
    tag_b = f"vf{nonce}b"
    tag_c = f"vf{nonce}c"
    hook_x = f"hx{nonce}"
    hook_y = f"hy{nonce}"
    hook_z = f"hz{nonce}"
    hook_w = f"hw{nonce}"

    dyn_plan = "\n".join(
        [
            _plan_header(),
            _plan_row(tag_a, 0.88, 0.12, 9, f"{hook_x}:1;{hook_y}:1", -1),
            _plan_row(tag_b, 0.31, 0.72, 6, f"{hook_z}:1", 2),
        ]
    )
    dyn_hooks = "\n".join(
        [
            _hooks_header(),
            _hook_row(hook_x, 0.50, "mul:1.08"),
            _hook_row(hook_y, 0.62, "add:-0.04"),
            _hook_row(hook_z, 0.28, "set:1.25"),
        ]
    )

    plan_rows = _parse_plan_text(dyn_plan)
    hooks_map = _parse_hooks_text(dyn_hooks)
    overlay = _overlay()
    expected = {c["tag"]: c for c in _model(overlay, plan_rows, hooks_map)}

    with _swap_inputs(dyn_plan, dyn_hooks):
        _run_harness()
        audit = _load_summary()
        got = {c["tag"]: c for c in audit["cases"]}
        with TRACE.open() as f:
            csv_tags = [r["tag"] for r in csv.DictReader(f)]

    assert tag_a in got
    assert tag_b in got
    assert static_tags.isdisjoint(got.keys())
    assert len(got) == 2

    for tag in (tag_a, tag_b):
        e = expected[tag]
        assert got[tag]["event_step"] == e["event_step"]
        assert got[tag]["metric_integral"] == pytest.approx(e["metric_integral"], rel=0, abs=1e-6)
        assert got[tag]["order_sensitive"] == e["order_sensitive"]

    assert audit["digest"] != baseline_digest
    assert audit["digest"] == _expected_digest([got[r["tag"]] for r in plan_rows])
    assert csv_tags == [tag_a, tag_b]

    variant_plan = "\n".join(
        [
            _plan_header(),
            _plan_row(tag_c, 1.2, 0.08, 11, f"{hook_w}:2", -1),
        ]
    )
    variant_hooks = "\n".join(
        [
            _hooks_header(),
            _hook_row(hook_w, 0.95, "mul:0.98"),
        ]
    )
    v_rows = _parse_plan_text(variant_plan)
    v_hooks = _parse_hooks_text(variant_hooks)
    v_exp = _model_case(v_rows[0], v_hooks, overlay, -1)

    with _swap_inputs(variant_plan, variant_hooks):
        _run_harness()
        v_audit = _load_summary()
        v_got = v_audit["cases"][0]

    assert v_got["tag"] == tag_c
    assert v_got["event_step"] == v_exp["event_step"]
    assert v_got["metric_integral"] == pytest.approx(v_exp["metric_integral"], rel=0, abs=1e-6)
    assert v_audit["digest"] != baseline_digest
    assert v_audit["digest"] != audit["digest"]


def test_dynamic_overlay_scale_defeats_static_metric_hardcode():
    """Verifier-generated metric_scale must rescale only metric-bearing rows in fresh plans."""
    nonce = _fresh_nonce()
    dyn_tag = f"vm{nonce}"
    hook_m = f"hm{nonce}"
    dyn_plan = "\n".join(
        [
            _plan_header(),
            _plan_row(dyn_tag, 0.75, 0.1, 7, f"{hook_m}:1", -1),
        ]
    )
    dyn_hooks = "\n".join([_hooks_header(), _hook_row(hook_m, 2.0, "none")])
    rows = _parse_plan_text(dyn_plan)
    hooks_map = _parse_hooks_text(dyn_hooks)
    scale_a = 1.0
    scale_b = 2.75
    exp_a = _model_case(rows[0], hooks_map, {**_overlay(), "metric_scale": scale_a}, -1)
    exp_b = _model_case(rows[0], hooks_map, {**_overlay(), "metric_scale": scale_b}, -1)

    prior_scale = _overlay()["metric_scale"]
    _set_overlay(metric_scale=scale_a)
    with _swap_inputs(dyn_plan, dyn_hooks):
        _run_harness()
        metric_a = _cases_by_tag()[dyn_tag]["metric_integral"]
    _set_overlay(metric_scale=scale_b)
    with _swap_inputs(dyn_plan, dyn_hooks):
        _run_harness()
        metric_b = _cases_by_tag()[dyn_tag]["metric_integral"]
    _set_overlay(metric_scale=prior_scale)
    _run_harness()

    assert metric_a == pytest.approx(exp_a["metric_integral"], rel=0, abs=1e-6)
    assert metric_b == pytest.approx(exp_b["metric_integral"], rel=0, abs=1e-6)
    assert metric_a != metric_b


def test_semantic_restart_chain_within_step_recheck():
    """After restart, later hooks on the same step must re-check crossing on updated y."""
    got = _cases_by_tag()
    exp_chain = next(c for c in _model() if c["tag"] == "restart_chain")
    exp_flip = next(c for c in _model() if c["tag"] == "tie_gate_flip")
    assert got["restart_chain"]["event_step"] == exp_chain["event_step"] == 4
    assert got["tie_gate_flip"]["event_step"] == exp_flip["event_step"] == 4
    assert got["restart_chain"]["metric_integral"] == pytest.approx(
        exp_chain["metric_integral"], rel=0, abs=1e-6
    )
    assert got["tie_gate_flip"]["metric_integral"] == pytest.approx(
        exp_flip["metric_integral"], rel=0, abs=1e-6
    )
    assert got["restart_chain"]["metric_integral"] != got["tie_gate_flip"]["metric_integral"]
    assert got["restart_chain"]["order_sensitive"] is True
    assert got["tie_gate_flip"]["order_sensitive"] is True


def test_semantic_gate_dent_registration_flip_isolates_metric():
    """Swapping dent/gate registration must change metric_integral without moving event_step."""
    got = _cases_by_tag()
    baseline = got["restart_chain"]
    flipped = got["tie_gate_flip"]
    assert baseline["event_step"] == flipped["event_step"]
    assert baseline["metric_integral"] != flipped["metric_integral"]
    exp_chain = next(c for c in _model() if c["tag"] == "restart_chain")
    exp_flip = next(c for c in _model() if c["tag"] == "tie_gate_flip")
    assert baseline["metric_integral"] == pytest.approx(exp_chain["metric_integral"], rel=0, abs=1e-6)
    assert flipped["metric_integral"] == pytest.approx(exp_flip["metric_integral"], rel=0, abs=1e-6)
    assert got["decay_integral"]["metric_integral"] == pytest.approx(
        next(c for c in _model() if c["tag"] == "decay_integral")["metric_integral"],
        rel=0,
        abs=1e-6,
    )


def test_semantic_restart_chain_couples_digest_and_summary():
    """restart_chain and tie_gate_flip must both reach summary_ok with distinct digest tokens."""
    audit = _load_summary()
    got = _cases_by_tag()
    for tag in ("restart_chain", "tie_gate_flip"):
        assert got[tag]["summary_ok"] is True
        assert got[tag]["report_line"] == "ok"
    tokens = {part.split(":", 1)[0]: part for part in audit["digest"].split("|")}
    assert tokens["restart_chain"] != tokens["tie_gate_flip"]
    assert audit["digest"] == _expected_digest(audit["cases"])


def test_dynamic_restart_chain_defeats_static_hardcode():
    """Fresh restart-chain rows must honor within-step hook re-evaluation, not static fixtures."""
    nonce = _fresh_nonce()
    hook_a = f"da{nonce}"
    hook_b = f"gb{nonce}"
    tag = f"rc{nonce}"
    dyn_plan = "\n".join(
        [
            _plan_header(),
            _plan_row(tag, 0.35, 0.95, 8, f"{hook_a}:1;{hook_b}:1", 4),
        ]
    )
    dyn_hooks = "\n".join(
        [
            _hooks_header(),
            _hook_row(hook_a, 0.40, "add:-0.20"),
            _hook_row(hook_b, 0.92, "mul:0.98"),
        ]
    )
    rows = _parse_plan_text(dyn_plan)
    hooks_map = _parse_hooks_text(dyn_hooks)
    overlay = _overlay()
    expected = _model_case(rows[0], hooks_map, overlay, -1)

    with _swap_inputs(dyn_plan, dyn_hooks):
        _run_harness()
        got = _cases_by_tag()[tag]

    assert got["event_step"] == expected["event_step"] == 4
    assert got["metric_integral"] == pytest.approx(expected["metric_integral"], rel=0, abs=1e-6)
    assert got["order_sensitive"] is True

    flip_plan = "\n".join(
        [
            _plan_header(),
            _plan_row(f"{tag}x", 0.35, 0.95, 8, f"{hook_b}:1;{hook_a}:1", 4),
        ]
    )
    flip_rows = _parse_plan_text(flip_plan)
    flip_exp = _model_case(flip_rows[0], hooks_map, overlay, -1)
    with _swap_inputs(flip_plan, dyn_hooks):
        _run_harness()
        flip_got = _cases_by_tag()[f"{tag}x"]

    assert flip_got["event_step"] == flip_exp["event_step"] == 4
    assert flip_got["metric_integral"] == pytest.approx(flip_exp["metric_integral"], rel=0, abs=1e-6)
    assert flip_got["metric_integral"] != got["metric_integral"]


def test_probe_chain_within_step_chaining():
    """Chain probe must apply hook effects in sorted order with running y."""
    hooks = _read_hooks()
    y_prev = 0.55
    y_post = 0.48
    order = "reclaim:1;mark:1"
    exp = _chain_model(y_prev, y_post, 1, 1.0, order, hooks, False, 1.0)
    got = float(
        _probe(
            {
                "TB_PROBE": "chain",
                "TB_Y_PREV": str(y_prev),
                "TB_Y": str(y_post),
                "TB_STEP": "1",
                "TB_Y0": "1.0",
                "TB_ORDER": order,
                "TB_RESTART": "0",
            }
        )
    )
    assert got == pytest.approx(exp, rel=0, abs=1e-9)


def test_probe_chain_restart_before_callbacks_secondary():
    """Chain probe with restart must apply restart before the callback phase."""
    hooks = _read_hooks()
    y_prev = 0.35
    y_post = 1e-9
    order = "dent:1;gate:1"
    exp = _chain_model(y_prev, y_post, 4, 0.35, order, hooks, True, 1.0)
    got = float(
        _probe(
            {
                "TB_PROBE": "chain",
                "TB_Y_PREV": str(y_prev),
                "TB_Y": str(y_post),
                "TB_STEP": "4",
                "TB_Y0": "0.35",
                "TB_ORDER": order,
                "TB_RESTART": "1",
                "TB_RESTART_Y": "1.0",
            }
        )
    )
    assert got == pytest.approx(exp, rel=0, abs=1e-9)


def test_checkpoint_carry_couples_later_row_metrics():
    """Prior row event_step must scale metrics on later rows through carry_gain."""
    rows = _read_plan()
    hooks = _read_hooks()
    overlay = _overlay()
    prev_es = -1
    expected = {}
    for row in rows:
        case = _model_case(row, hooks, overlay, prev_es)
        expected[row["tag"]] = case
        prev_es = case["event_step"]
    got = _cases_by_tag()
    assert got["order_sensitive"]["metric_integral"] == pytest.approx(
        expected["order_sensitive"]["metric_integral"], rel=0, abs=1e-6
    )
    assert expected["order_sensitive"]["metric_integral"] != _model_case(
        rows[4], hooks, overlay, -1
    )["metric_integral"]


def test_checkpoint_file_drives_carry_not_memory_only():
    """Harness must read carry from ode_checkpoint.json between plan rows."""
    rows = _read_plan()
    hooks = _read_hooks()
    overlay = _overlay()
    prev_es = -1
    expected = {}
    for row in rows:
        case = _model_case(row, hooks, overlay, prev_es)
        expected[row["tag"]] = case
        prev_es = case["event_step"]
    got = _cases_by_tag()
    assert got["tie_gate_flip"]["metric_integral"] == pytest.approx(
        expected["tie_gate_flip"]["metric_integral"], rel=0, abs=1e-6
    )
    cp = APP / "cfg" / "ode_checkpoint.json"
    assert cp.exists()
    state = json.loads(cp.read_text())
    assert state["last_event_step"] == got[rows[-1]["tag"]]["event_step"]


def test_checkpoint_mutation_isolates_unrelated_rows():
    """Changing an early row y0 must not alter a later row when carry path unchanged."""
    baseline = _cases_by_tag()
    plan_backup = PLAN.read_text()
    row0 = _read_plan()[0]
    muted = _plan_row(row0["tag"], 0.10, row0["dt"], row0["steps"], row0["callback_order"], row0["restart_step"])
    muted_plan = "\n".join([_plan_header(), muted] + PLAN.read_text().splitlines()[2:]) + "\n"
    PLAN.write_text(muted_plan)
    try:
        _run_harness()
        got = _cases_by_tag()
        assert got["tie_gate_flip"]["metric_integral"] == pytest.approx(
            baseline["tie_gate_flip"]["metric_integral"], rel=0, abs=1e-6
        )
        assert got["step0_fire"]["event_step"] != baseline["step0_fire"]["event_step"]
    finally:
        PLAN.write_text(plan_backup)
        _run_harness()


def test_near_miss_chain_restart_after_hooks_fails():
    """Applying restart before hook chaining would diverge from dent/gate restart_chain."""
    hooks = _read_hooks()
    y_prev = 0.35
    y_post = 1e-9
    order = "dent:1;gate:1"
    wrong = y_post
    for cb in sorted(_parse_callbacks(order), key=lambda c: (c["load_order"], c["registration"])):
        hook = hooks[cb["name"]]
        if _hook_fires(y_prev, wrong, hook["threshold"], 4, 0.35):
            wrong = _apply_effect(wrong, hook["on_fire"])
    wrong = 1.0
    got = float(
        _probe(
            {
                "TB_PROBE": "chain",
                "TB_Y_PREV": str(y_prev),
                "TB_Y": str(y_post),
                "TB_STEP": "4",
                "TB_Y0": "0.35",
                "TB_ORDER": order,
                "TB_RESTART": "1",
                "TB_RESTART_Y": "1.0",
            }
        )
    )
    assert got != pytest.approx(wrong, rel=0, abs=1e-9)


def test_mutation_carry_gain_scales_order_sensitive_only():
    """carry_gain mutation must rescale rows after a firing predecessor, not decay_integral."""
    baseline = _cases_by_tag()
    prior_gain = _overlay()["carry_gain"]
    _set_overlay(carry_gain=prior_gain + 0.02)
    try:
        _run_harness()
        got = _cases_by_tag()
        overlay = _overlay()
        rows = _read_plan()
        prev_es = -1
        exp_sensitive = None
        for row in rows:
            case = _model_case(row, _read_hooks(), overlay, prev_es)
            if row["tag"] == "order_sensitive":
                exp_sensitive = case["metric_integral"]
            prev_es = case["event_step"]
        assert got["order_sensitive"]["metric_integral"] != baseline["order_sensitive"]["metric_integral"]
        assert got["order_sensitive"]["metric_integral"] == pytest.approx(exp_sensitive, rel=0, abs=1e-6)
        assert got["decay_integral"]["metric_integral"] == pytest.approx(
            baseline["decay_integral"]["metric_integral"], rel=0, abs=1e-6
        )
    finally:
        _set_overlay(carry_gain=prior_gain)
        _run_harness()
