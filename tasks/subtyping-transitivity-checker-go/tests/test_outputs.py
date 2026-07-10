import json
import os
import subprocess


OUTPUT_PATH = "/app/output/results.json"

EXPECTED_TOTAL_RULES = 11
EXPECTED_OBLIGATION_COUNT = 7
EXPECTED_UNPROVABLE_COUNT = 0
EXPECTED_TRANSITIVITY_HOLDS = True
EXPECTED_BREAKING_RULES = []

EXPECTED_OBLIGATIONS = [
    {"sub": "Bool", "super": "Hashable", "via": "Comparable", "is_provable": True},
    {"sub": "Comparable", "super": "Object", "via": "Hashable", "is_provable": True},
    {"sub": "Float", "super": "Object", "via": "Number", "is_provable": True},
    {"sub": "Nat", "super": "Number", "via": "Int", "is_provable": True},
    {"sub": "Nat", "super": "Object", "via": "Int", "is_provable": True},
    {"sub": "Printable", "super": "Object", "via": "Displayable", "is_provable": True},
    {"sub": "String", "super": "Displayable", "via": "Printable", "is_provable": True},
]


def load_output():
    """Load and parse the output JSON file."""
    with open(OUTPUT_PATH) as f:
        return json.load(f)


def test_output_file_exists():
    """Verify that the output file was created."""
    assert os.path.exists(OUTPUT_PATH), f"Output file not found at {OUTPUT_PATH}"


def test_output_valid_json():
    """Verify that the output is valid JSON with required top-level keys."""
    data = load_output()
    required_keys = ["total_rules", "obligations", "unprovable_count",
                     "transitivity_holds", "breaking_rules"]
    for key in required_keys:
        assert key in data, f"Missing required key: {key}"


def test_total_rules():
    """Verify total_rules includes all 11 rules from input."""
    data = load_output()
    assert data["total_rules"] == EXPECTED_TOTAL_RULES


def test_obligation_count():
    """Verify the correct number of obligations are generated."""
    data = load_output()
    assert len(data["obligations"]) == EXPECTED_OBLIGATION_COUNT


def test_unprovable_count():
    """Verify unprovable_count is zero since all obligations are provable."""
    data = load_output()
    assert data["unprovable_count"] == EXPECTED_UNPROVABLE_COUNT


def test_transitivity_holds():
    """Verify transitivity_holds is true when unprovable_count is zero."""
    data = load_output()
    assert data["transitivity_holds"] is EXPECTED_TRANSITIVITY_HOLDS


def test_breaking_rules_empty():
    """Verify breaking_rules is empty when all obligations are provable."""
    data = load_output()
    assert data["breaking_rules"] == EXPECTED_BREAKING_RULES


def test_obligations_sorted():
    """Verify obligations are sorted by sub, then super, then via."""
    data = load_output()
    obligations = data["obligations"]
    for i in range(len(obligations) - 1):
        a = (obligations[i]["sub"], obligations[i]["super"], obligations[i]["via"])
        b = (obligations[i + 1]["sub"], obligations[i + 1]["super"], obligations[i + 1]["via"])
        assert a <= b, f"Obligations not sorted: {a} > {b}"


def test_obligation_schema():
    """Verify each obligation has required fields with correct types."""
    data = load_output()
    for o in data["obligations"]:
        assert "sub" in o, "Missing sub field"
        assert "super" in o, "Missing super field"
        assert "via" in o, "Missing via field"
        assert "is_provable" in o, "Missing is_provable field"
        assert isinstance(o["sub"], str)
        assert isinstance(o["super"], str)
        assert isinstance(o["via"], str)
        assert isinstance(o["is_provable"], bool)


def test_all_obligations_provable():
    """Verify all obligations have is_provable set to true."""
    data = load_output()
    for o in data["obligations"]:
        assert o["is_provable"] is True, (
            f"Obligation {o['sub']}<:{o['super']} via {o['via']} "
            f"should be provable"
        )


def test_obligation_float_object():
    """Verify Float<:Object via Number obligation exists and is provable."""
    data = load_output()
    found = [o for o in data["obligations"]
             if o["sub"] == "Float" and o["super"] == "Object"]
    assert len(found) == 1
    assert found[0]["via"] == "Number"
    assert found[0]["is_provable"] is True


def test_obligation_nat_number():
    """Verify Nat<:Number via Int obligation exists and is provable."""
    data = load_output()
    found = [o for o in data["obligations"]
             if o["sub"] == "Nat" and o["super"] == "Number"]
    assert len(found) == 1
    assert found[0]["via"] == "Int"
    assert found[0]["is_provable"] is True


def test_obligation_nat_object():
    """Verify Nat<:Object via Int obligation exists and is provable."""
    data = load_output()
    found = [o for o in data["obligations"]
             if o["sub"] == "Nat" and o["super"] == "Object"]
    assert len(found) == 1
    assert found[0]["via"] == "Int"
    assert found[0]["is_provable"] is True


def test_obligation_bool_hashable():
    """Verify Bool<:Hashable via Comparable obligation exists and is provable."""
    data = load_output()
    found = [o for o in data["obligations"]
             if o["sub"] == "Bool" and o["super"] == "Hashable"]
    assert len(found) == 1
    assert found[0]["via"] == "Comparable"
    assert found[0]["is_provable"] is True


def test_obligation_string_displayable():
    """Verify String<:Displayable via Printable obligation exists."""
    data = load_output()
    found = [o for o in data["obligations"]
             if o["sub"] == "String" and o["super"] == "Displayable"]
    assert len(found) == 1
    assert found[0]["via"] == "Printable"
    assert found[0]["is_provable"] is True


def test_no_obligation_for_direct_rules():
    """Verify no obligation is generated for Int<:Object (direct rule R03 exists)."""
    data = load_output()
    found = [o for o in data["obligations"]
             if o["sub"] == "Int" and o["super"] == "Object"]
    assert len(found) == 0, (
        "Int<:Object should not generate an obligation since R03 is a direct rule"
    )


def test_deterministic_output():
    """Verify output structure is consistent and deterministic."""
    data = load_output()
    assert isinstance(data["total_rules"], int)
    assert isinstance(data["obligations"], list)
    assert isinstance(data["unprovable_count"], int)
    assert isinstance(data["transitivity_holds"], bool)
    assert isinstance(data["breaking_rules"], list)
    assert data["unprovable_count"] == EXPECTED_UNPROVABLE_COUNT
    assert data["transitivity_holds"] == EXPECTED_TRANSITIVITY_HOLDS


def _run_alt(path):
    """Run the checker with alternate input data."""
    result = subprocess.run(
        ["/app/bin/transitivity-checker", path, "/tmp/alt_results.json"],
        capture_output=True, timeout=30,
    )
    assert result.returncode == 0, f"Alt run failed: {result.stderr.decode()}"
    with open("/tmp/alt_results.json") as f:
        return json.load(f)


def test_alt_total_rules():
    """Alt data: 10 rules including conditional A07 must all be counted."""
    data = _run_alt("/tests/alt_rules.json")
    assert data["total_rules"] == 10


def test_alt_obligation_count():
    """Alt data: 7 obligations from diamond and chain structures."""
    data = _run_alt("/tests/alt_rules.json")
    assert len(data["obligations"]) == 7


def test_alt_all_provable():
    """Alt data: all obligations are provable since graph is connected per chain."""
    data = _run_alt("/tests/alt_rules.json")
    assert data["unprovable_count"] == 0
    assert data["transitivity_holds"] is True


def test_alt_conditional_rule_included():
    """Conditional rule A07 (Kitten<:Cat) must be included; generates obligations."""
    data = _run_alt("/tests/alt_rules.json")
    kitten_obs = [o for o in data["obligations"] if o["sub"] == "Kitten"]
    assert len(kitten_obs) == 3, (
        "Kitten should generate 3 obligations (via Cat to Animal, Being, Pet)"
    )


def test_alt_no_obligation_for_direct_cat_being():
    """Cat<:Being has direct rule A03, so no obligation for Cat<:Being via Animal."""
    data = _run_alt("/tests/alt_rules.json")
    found = [o for o in data["obligations"]
             if o["sub"] == "Cat" and o["super"] == "Being" and o["via"] == "Animal"]
    assert len(found) == 0, "Direct rule A03 should prevent this obligation"


def test_edge_deduplication():
    """E01 and E03 both define Alpha<:Beta; only one Alpha<:Gamma obligation generated."""
    data = _run_alt("/tests/edge_rules.json")
    alpha_gamma = [o for o in data["obligations"]
                   if o["sub"] == "Alpha" and o["super"] == "Gamma"]
    assert len(alpha_gamma) == 1, (
        "Duplicate rules Alpha<:Beta should produce only one obligation for Alpha<:Gamma"
    )


def test_edge_total_rules_includes_duplicates():
    """All 8 rules counted even though E01 and E03 define same relationship."""
    data = _run_alt("/tests/edge_rules.json")
    assert data["total_rules"] == 8


def test_edge_obligation_count():
    """Edge data: 4 obligations (Alpha<:Gamma, Beta<:Omega, Mu<:Sigma, Phi<:Theta)."""
    data = _run_alt("/tests/edge_rules.json")
    assert len(data["obligations"]) == 4


def test_edge_breaking_rules_empty():
    """Edge data: no unprovable obligations, so breaking_rules empty."""
    data = _run_alt("/tests/edge_rules.json")
    assert data["breaking_rules"] == []


def test_config_settings_authoritative():
    """Config from settings.toml must be used; include_conditional=true."""
    data = load_output()
    # If profile override applied (include_conditional=false), R09 would be excluded
    # and total_rules would be 10, not 11. Having 11 proves settings.toml is used.
    assert data["total_rules"] == 11


def test_repeated_runs_deterministic():
    """Running the tool twice produces identical output."""
    result1 = subprocess.run(
        ["/app/bin/transitivity-checker", "data/rules.json", "/tmp/det1.json"],
        capture_output=True, cwd="/app", timeout=30,
    )
    result2 = subprocess.run(
        ["/app/bin/transitivity-checker", "data/rules.json", "/tmp/det2.json"],
        capture_output=True, cwd="/app", timeout=30,
    )
    assert result1.returncode == 0
    assert result2.returncode == 0
    with open("/tmp/det1.json") as f:
        d1 = json.load(f)
    with open("/tmp/det2.json") as f:
        d2 = json.load(f)
    assert d1 == d2, "Output must be deterministic across repeated runs"


def test_binary_no_args_exits_nonzero():
    """Running without arguments must exit non-zero."""
    result = subprocess.run(
        ["/app/bin/transitivity-checker"],
        capture_output=True, timeout=10,
    )
    assert result.returncode != 0


def test_breaking_rules_is_sorted():
    """breaking_rules array must be sorted lexicographically."""
    data = load_output()
    rules = data["breaking_rules"]
    assert rules == sorted(rules), "breaking_rules must be sorted"


def test_stress_total_rules():
    """Stress data: all 15 rules including conditional S09 are counted."""
    data = _run_alt("/tests/stress_rules.json")
    assert data["total_rules"] == 15


def test_stress_obligation_count():
    """Stress data: exactly 11 obligations from 5-level chain and diamond."""
    data = _run_alt("/tests/stress_rules.json")
    assert len(data["obligations"]) == 11


def test_stress_direct_rule_suppresses_obligation():
    """Byte<:Int has direct rule S06, so Byte<:Int via Short NOT generated."""
    data = _run_alt("/tests/stress_rules.json")
    found = [o for o in data["obligations"]
             if o["sub"] == "Byte" and o["super"] == "Int"]
    assert len(found) == 0, "Direct rule S06 must suppress Byte<:Int obligation"


def test_stress_long_chain_generates_only_adjacent_pair_obligations():
    """Only adjacent rule pairs generate obligations, not transitive chains."""
    data = _run_alt("/tests/stress_rules.json")
    # Byte<:BigInt is NOT an obligation because no single rule pair yields it
    # (Byte→Int + Int→Long gives Byte<:Long, not Byte<:BigInt)
    found = [o for o in data["obligations"]
             if o["sub"] == "Byte" and o["super"] == "BigInt"]
    assert len(found) == 0, (
        "Byte<:BigInt is not from any direct rule pair, should not be an obligation"
    )


def test_stress_byte_serializable_via_printable():
    """Byte<:Serializable via Printable exists (from S10+S11 pair)."""
    data = _run_alt("/tests/stress_rules.json")
    found = [o for o in data["obligations"]
             if o["sub"] == "Byte" and o["super"] == "Serializable"
             and o["via"] == "Printable"]
    assert len(found) == 1
    assert found[0]["is_provable"] is True


def test_stress_no_byte_serializable_via_numeric():
    """No Byte<:Serializable via Numeric because no rule Byte<:Numeric exists."""
    data = _run_alt("/tests/stress_rules.json")
    found = [o for o in data["obligations"]
             if o["sub"] == "Byte" and o["super"] == "Serializable"
             and o["via"] == "Numeric"]
    assert len(found) == 0, (
        "There is no rule Byte<:Numeric, so no pair produces this obligation"
    )


def test_stress_multiple_paths_single_obligation_per_via():
    """Byte can reach Serializable via multiple paths but obligations are per rule-pair via."""
    data = _run_alt("/tests/stress_rules.json")
    byte_ser = [o for o in data["obligations"]
                if o["sub"] == "Byte" and o["super"] == "Serializable"]
    # Only via Printable (from S10+S11), NOT via Numeric (no Byte→Numeric rule)
    assert len(byte_ser) == 1
    assert byte_ser[0]["via"] == "Printable"


def test_stress_all_provable():
    """All 11 obligations must be provable since graph is connected."""
    data = _run_alt("/tests/stress_rules.json")
    assert data["unprovable_count"] == 0
    assert data["transitivity_holds"] is True
    for o in data["obligations"]:
        assert o["is_provable"] is True
