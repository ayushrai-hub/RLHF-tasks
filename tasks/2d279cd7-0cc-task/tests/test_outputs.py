import os
import json
import subprocess
import hashlib
from contextlib import contextmanager

def run_js_fn(fn_name, module_path, *args):
    js_code = f"""
    const fn = require('{module_path}');
    console.log(JSON.stringify(fn(...{json.dumps(args)})));
    """
    res = subprocess.run(["node", "-e", js_code], capture_output=True, text=True, check=True)
    return json.loads(res.stdout.strip())

def run_merge(base, extra):
    js_code = f"""
    const {{ op_e }} = require('/app/locepsilon/phase_five');
    console.log(JSON.stringify(op_e(...{json.dumps([base, extra])})));
    """
    res = subprocess.run(["node", "-e", js_code], capture_output=True, text=True, check=True)
    return json.loads(res.stdout.strip())

def run_phase_f(action, payload=None):
    js_code = f"""
    const {{ op_f }} = require('/app/locepsilon/phase_five');
    console.log(JSON.stringify(op_f({json.dumps(action)}, {json.dumps(payload)})));
    """
    res = subprocess.run(["node", "-e", js_code], capture_output=True, text=True, check=True)
    return json.loads(res.stdout.strip())

def run_enumerate(flags, constraints):
    js_code = f"""
    const op_g = require('/app/loczeta/phase_six');
    const op_b = require('/app/locbeta/phase_two');
    const flags = {json.dumps(flags)};
    const constraints = {json.dumps(constraints)};
    console.log(JSON.stringify(op_g(flags, constraints, (expr, f) => op_b(expr, f))));
    """
    res = subprocess.run(["node", "-e", js_code], capture_output=True, text=True, check=True)
    return json.loads(res.stdout.strip())

def run_pipeline():
    res = subprocess.run(["node", "/app/src/main.js"], capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

def load_results():
    with open("/app/output/results.json", "r") as f:
        return json.load(f)

def load_input_config():
    with open("/app/data/input.json", "r") as f:
        return json.load(f)

def merged_valid_count(base, extra):
    merged = run_merge(base, extra)
    return len(run_enumerate(merged["flags"], merged["constraints"]))

@contextmanager
def extra_config(content):
    extra_path = "/app/data/extra.json"
    backup = None
    if os.path.exists(extra_path):
        with open(extra_path, "r") as f:
            backup = f.read()
    with open(extra_path, "w") as f:
        json.dump(content, f)
    try:
        yield
    finally:
        if backup is None:
            if os.path.exists(extra_path):
                os.remove(extra_path)
        else:
            with open(extra_path, "w") as f:
                f.write(backup)

@contextmanager
def scenario_ckpt(payload):
    ckpt_path = "/app/data/.scenario_ckpt"
    backup = None
    if os.path.exists(ckpt_path):
        with open(ckpt_path, "r") as f:
            backup = f.read()
    with open(ckpt_path, "w") as f:
        json.dump(payload, f)
    try:
        yield
    finally:
        if backup is None:
            if os.path.exists(ckpt_path):
                os.remove(ckpt_path)
        else:
            with open(ckpt_path, "w") as f:
                f.write(backup)

def scenario_sort_key(scenario):
    flags = scenario["flags"]
    return tuple((name, flags[name]) for name in sorted(flags.keys()))

def derived_signature_hash(scenarios):
    sorted_scenarios = sorted(scenarios, key=scenario_sort_key)
    sig_parts = []
    for scenario in sorted_scenarios:
        if scenario["cycle_nodes"]:
            sig_parts.append("cycle:" + ",".join(scenario["cycle_nodes"]))
        else:
            sig_parts.append(",".join(scenario["ordering"]))
    return hashlib.sha256(";".join(sig_parts).encode()).hexdigest()

def assert_report_consistency(data):
    summary = data["summary"]
    scenarios = data["scenarios"]
    assert summary["scenarios_checked"] == len(scenarios)
    assert summary["cyclic_count"] == sum(1 for s in scenarios if s["cycle_nodes"])
    assert summary["acyclic_count"] == len(scenarios) - summary["cyclic_count"]
    assert scenarios == sorted(scenarios, key=scenario_sort_key)
    assert summary["signature_hash"] == derived_signature_hash(scenarios)

def test_s1_implicit_cross_branch_secondary_slot():
    """Validate test_s1_implicit_cross_branch_secondary_slot behavior against the published contract."""
    branches = [
        [{"id": "n1", "resources": ["z", "shared"]}],
        [{"id": "n2", "resources": ["shared"]}],
    ]
    result = run_js_fn("op_a", "/app/localpha/phase_one.js", branches, [])
    assert result == [{"from": "n1", "to": "n2"}]

def test_s2_implicit_multi_group_cache_net():
    """Validate test_s2_implicit_multi_group_cache_net behavior against the published contract."""
    branches = [
        [{"id": "n1", "resources": ["net", "cache"]}],
        [{"id": "n2", "resources": ["cache"]}],
    ]
    result = run_js_fn("op_a", "/app/localpha/phase_one.js", branches, ["cache"])
    assert result == [{"from": "n1", "to": "n2"}]

def test_s3_implicit_no_edges_when_locks_disjoint():
    """Validate test_s3_implicit_no_edges_when_locks_disjoint behavior against the published contract."""
    branches = [
        [{"id": "n1", "resources": ["alpha"]}],
        [{"id": "n2", "resources": ["beta"]}],
    ]
    result = run_js_fn("op_a", "/app/localpha/phase_one.js", branches, [])
    assert result == []

def test_s4_expr_operator_precedence():
    """Validate test_s4_expr_operator_precedence behavior against the published contract."""
    expr = "feat_a & feat_b | feat_c"
    assert run_js_fn("op_b", "/app/locbeta/phase_two.js", expr, {"feat_a": False, "feat_b": True, "feat_c": True}) is True
    assert run_js_fn("op_b", "/app/locbeta/phase_two.js", expr, {"feat_a": False, "feat_b": True, "feat_c": False}) is False

def test_s5_expr_negated_parenthesis():
    """Validate test_s5_expr_negated_parenthesis behavior against the published contract."""
    assert run_js_fn("op_b", "/app/locbeta/phase_two.js", "!(x&y)", {"x": True, "y": False}) is True

def test_s6_expr_whitespace_only():
    """Validate test_s6_expr_whitespace_only behavior against the published contract."""
    assert run_js_fn("op_b", "/app/locbeta/phase_two.js", "  \t ", {"x": True}) is True

def test_s7_cycle_witness_mutual_exclusion():
    """Validate test_s7_cycle_witness_mutual_exclusion behavior against the published contract."""
    edges = [["A", "B"], ["B", "C"], ["C", "D"], ["D", "A"]]
    conditions = {"A->B": "p", "B->C": "p", "C->D": "p", "D->A": "!p"}
    assert run_js_fn("op_c", "/app/locgamma/phase_three.js", edges, conditions) == []

def test_s8_cycle_witness_coupled_four_edge():
    """Validate test_s8_cycle_witness_coupled_four_edge behavior against the published contract."""
    edges = [["A", "B"], ["B", "C"], ["C", "D"], ["D", "A"]]
    conditions = {
        "A->B": "a",
        "B->C": "b",
        "C->D": "b",
        "D->A": "!(a & b)",
    }
    assert run_js_fn("op_c", "/app/locgamma/phase_three.js", edges, conditions) == []

def test_s9_cycle_witness_two_node():
    """Validate test_s9_cycle_witness_two_node behavior against the published contract."""
    edges = [["A", "B"], ["B", "A"]]
    conditions = {"A->B": "x", "B->A": "y | !x"}
    result = run_js_fn("op_c", "/app/locgamma/phase_three.js", edges, conditions)
    assert len(result) == 1 and sorted(result[0]) == ["A", "B"]

def test_s10_cycle_witness_triangle_shared_flag():
    """Validate test_s10_cycle_witness_triangle_shared_flag behavior against the published contract."""
    edges = [["A", "B"], ["B", "C"], ["C", "A"]]
    conditions = {"A->B": "f", "B->C": "f", "C->A": "f"}
    result = run_js_fn("op_c", "/app/locgamma/phase_three.js", edges, conditions)
    assert len(result) == 1 and sorted(result[0]) == ["A", "B", "C"]

def test_s11_format_scenario_and_field_order():
    """Validate test_s11_format_scenario_and_field_order behavior against the published contract."""
    scenarios = [
        {
            "flags": {"b": True, "a": False},
            "cycle_nodes": ["z", "y"],
            "ordering": [],
            "implicit_edges": [{"from": "b", "to": "a"}],
        },
        {
            "flags": {"b": False, "a": False},
            "cycle_nodes": [],
            "ordering": ["c", "a"],
            "implicit_edges": [],
        },
    ]
    result = run_js_fn("op_d", "/app/locdelta/phase_four.js", scenarios)
    assert result["scenarios"][0]["flags"] == {"a": False, "b": False}
    assert result["scenarios"][1]["cycle_nodes"] == ["y", "z"]

def test_s12_format_signature_hash():
    """Validate test_s12_format_signature_hash behavior against the published contract."""
    scenarios = [
        {"flags": {"k": True}, "cycle_nodes": ["B", "A"], "ordering": [], "implicit_edges": []},
        {"flags": {"k": False}, "cycle_nodes": [], "ordering": ["A", "B"], "implicit_edges": []},
    ]
    expected = hashlib.sha256(b"A,B;cycle:A,B").hexdigest()
    result = run_js_fn("op_d", "/app/locdelta/phase_four.js", scenarios)
    assert result["summary"]["signature_hash"] == expected

def test_s13_format_cycle_ordering_empty():
    """Validate test_s13_format_cycle_ordering_empty behavior against the published contract."""
    scenarios = [
        {"flags": {"k": True}, "cycle_nodes": ["c", "a", "b"], "ordering": ["x"], "implicit_edges": []},
    ]
    result = run_js_fn("op_d", "/app/locdelta/phase_four.js", scenarios)
    assert result["scenarios"][0]["cycle_nodes"] == ["a", "b", "c"]
    assert result["scenarios"][0]["ordering"] == []

def test_s14_fresh_pipeline_overwrites_stale():
    """Validate test_s14_fresh_pipeline_overwrites_stale behavior against the published contract."""
    out_file = "/app/output/results.json"
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, "w") as f:
        f.write('{"_probe_sentinel": true}')
    code, _, stderr = run_pipeline()
    assert code == 0, stderr
    with open(out_file, "r") as f:
        data = json.load(f)
    assert "_probe_sentinel" not in data

def test_s15_consecutive_runs_identical():
    """Validate test_s15_consecutive_runs_identical behavior against the published contract."""
    run_pipeline()
    with open("/app/output/results.json", "r") as f:
        first = f.read()
    run_pipeline()
    with open("/app/output/results.json", "r") as f:
        second = f.read()
    assert first == second

def test_s16_e2e_primary_golden():
    """Validate test_s16_e2e_primary_golden behavior against the published contract."""
    base = load_input_config()
    with extra_config({}):
        code, _, stderr = run_pipeline()
        assert code == 0, stderr
        data = load_results()
        assert_report_consistency(data)
        valid_count = len(run_enumerate(base["flags"], base["constraints"]))
        assert data["summary"]["scenarios_checked"] == valid_count
        probe_flags = {name: False for name in base["flags"]}
        match = next(s for s in data["scenarios"] if s["flags"] == probe_flags)
        assert match["cycle_nodes"] == []
        implicit = {(e["from"], e["to"]) for e in match["implicit_edges"]}
        assert ("task_A", "task_B") in implicit
        assert ("task_F", "task_G") in implicit
        assert data["summary"]["cyclic_count"] > 0

def test_s17_e2e_extra_merge_golden():
    """Validate test_s17_e2e_extra_merge_golden behavior against the published contract."""
    base = load_input_config()
    fixture_path = os.path.join("/app", "data", "extra_merge_fixture.json")
    with open(fixture_path, "r") as f:
        payload = json.load(f)
    with extra_config({}):
        run_pipeline()
        primary = load_results()
    with extra_config(payload):
        code, _, stderr = run_pipeline()
        assert code == 0, stderr
        data = load_results()
        assert_report_consistency(data)
        assert data["summary"]["scenarios_checked"] == merged_valid_count(base, payload)
        assert data["summary"]["scenarios_checked"] < primary["summary"]["scenarios_checked"]
        assert data["summary"]["signature_hash"] != primary["summary"]["signature_hash"]

def test_s18_e2e_cyclic_signature():
    """Validate test_s18_e2e_cyclic_signature behavior against the published contract."""
    with extra_config({}):
        code, _, stderr = run_pipeline()
        assert code == 0, stderr
        data = load_results()
        cyclic = [s for s in data["scenarios"] if s["cycle_nodes"]]
        assert len(cyclic) == data["summary"]["cyclic_count"]
        for scenario in cyclic:
            assert set(scenario["cycle_nodes"]) == {"task_P", "task_Q", "task_R"}
            assert scenario["ordering"] == []

def test_s19_e2e_extra_cyclic_elimination():
    """Validate test_s19_e2e_extra_cyclic_elimination behavior against the published contract."""
    fixture_path = os.path.join("/app", "data", "extra_cyclic_fixture.json")
    with open(fixture_path, "r") as f:
        payload = json.load(f)
    with extra_config({}):
        run_pipeline()
        primary = load_results()
    with extra_config(payload):
        run_pipeline()
        merged = load_results()
    assert primary["summary"]["cyclic_count"] > 0
    assert merged["summary"]["cyclic_count"] == 0
    assert merged["summary"]["scenarios_checked"] < primary["summary"]["scenarios_checked"]

def test_s20_merge_overlay_append():
    """Validate test_s20_merge_overlay_append behavior against the published contract."""
    base = {"flags": ["a"], "constraints": ["!(a&b)"], "parallel_groups": [{"branches": [["x"]], "merge_node": "m1"}]}
    extra = {"constraints": ["b"], "parallel_groups": [{"branches": [["y"]], "merge_node": "m2"}]}
    merged = run_merge(base, extra)
    assert len(merged["constraints"]) == 2
    assert len(merged["parallel_groups"]) == 2

def test_s21_checkpoint_digest_invalidation():
    """Validate test_s21_checkpoint_digest_invalidation behavior against the published contract."""
    base = load_input_config()
    digest = run_phase_f("digest", base)
    with scenario_ckpt({"offset": 6, "digest": digest}):
        fixture_path = os.path.join("/app", "data", "extra_merge_fixture.json")
        with open(fixture_path, "r") as f:
            payload = json.load(f)
        with extra_config(payload):
            code, _, stderr = run_pipeline()
            assert code == 0, stderr
            data = load_results()
            assert data["summary"]["scenarios_checked"] == merged_valid_count(base, payload)

def test_s22_expr_unknown_identifier_false():
    """Validate test_s22_expr_unknown_identifier_false behavior against the published contract."""
    assert run_js_fn("op_b", "/app/locbeta/phase_two.js", "missing & a", {"a": True}) is False

def test_s23_enumeration_flag_bit_order():
    """Validate test_s23_enumeration_flag_bit_order behavior against the published contract."""
    flags = ["a", "b", "c"]
    constraints = ["!(a & b & c)"]
    scenarios = run_enumerate(flags, constraints)
    assert len(scenarios) == 7
    index_one = next(s for s in scenarios if sum(1 for v in s.values() if v) == 1)
    assert index_one == {"a": True, "b": False, "c": False}

def dummy_reference():
    import subprocess
    subprocess.run(["node", "/app/src/main.js"])
