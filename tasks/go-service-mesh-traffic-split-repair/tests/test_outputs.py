"""Verifier tests for the Go traffic splitter repair task."""
import json
import os
from collections import Counter
from pathlib import Path
from subprocess import run

OUTPUT_PATH = Path("/app/output/routing_result.json")
CONFIG_PATH = Path("/app/environment/config/split_rules.json")
REQUESTS_PATH = Path("/app/environment/data/requests.json")
SPLITTER_DIR = Path("/app/environment/splitter")
BINARY_PATH = Path("/app/bin/splitter")

ENABLED_BACKEND = "canary-v2"
AUTHORIZED_BACKEND = "canary-v3"
STABLE_BACKEND = "stable"
DISABLED_BACKEND = "deprecated-v1"
FALLBACK_BACKEND = "fallback-pool"
BEARER_TOKEN = "Bearer test-token"


def _load_output():
    assert OUTPUT_PATH.is_file(), f"routing output missing at {OUTPUT_PATH}"
    with OUTPUT_PATH.open() as f:
        return json.load(f)


def _load_config():
    with CONFIG_PATH.open() as f:
        return json.load(f)


def _load_requests():
    with REQUESTS_PATH.open() as f:
        return json.load(f)


def _is_enabled(backend):
    return backend.get("enabled", True) is not False and backend.get("weight", 0) > 0


def _route_map(data):
    return {row["request_id"]: row for row in data["routed_requests"]}


# ---- Output structure and schema ----


def test_output_file_exists():
    """Verify the rebuilt binary produced the required JSON output file."""
    assert OUTPUT_PATH.is_file(), f"expected output at {OUTPUT_PATH}"


def test_output_is_valid_json_object():
    """Verify the output file is parseable JSON with an object at the top level."""
    assert isinstance(_load_output(), dict)


def test_output_has_routed_requests_and_summary():
    """Verify the output includes the two top-level contract sections."""
    data = _load_output()
    assert set(data) == {"routed_requests", "summary"}
    assert isinstance(data["routed_requests"], list)
    assert isinstance(data["summary"], dict)


def test_routed_request_schema_and_order():
    """Verify each routed request has string fields and preserves input order."""
    data = _load_output()
    reqs = _load_requests()
    routed = data["routed_requests"]
    assert len(routed) == len(reqs)
    assert [r["request_id"] for r in routed] == [r["id"] for r in reqs]
    for row in routed:
        assert set(row) == {"request_id", "backend", "rule_name"}
        assert isinstance(row["request_id"], str)
        assert isinstance(row["backend"], str)
        assert isinstance(row["rule_name"], str)


def test_summary_schema_and_types():
    """Verify summary fields have the documented names and JSON types."""
    summary = _load_output()["summary"]
    assert set(summary) == {"total_requests", "backend_counts", "expected_weights", "balanced"}
    assert isinstance(summary["total_requests"], int)
    assert isinstance(summary["backend_counts"], dict)
    assert isinstance(summary["expected_weights"], dict)
    assert isinstance(summary["balanced"], bool)
    assert all(isinstance(k, str) and isinstance(v, int) for k, v in summary["backend_counts"].items())
    assert all(isinstance(k, str) and isinstance(v, int) for k, v in summary["expected_weights"].items())


def test_summary_total_matches_input_size():
    """Verify summary.total_requests equals the number of input requests."""
    assert _load_output()["summary"]["total_requests"] == len(_load_requests())


# ---- Routing behavior from the provided fixture ----


def test_every_request_has_exactly_one_routing_result():
    """Verify no input request is missing or duplicated in routed_requests."""
    data = _load_output()
    reqs = _load_requests()
    counts = Counter(row["request_id"] for row in data["routed_requests"])
    assert set(counts) == {req["id"] for req in reqs}
    assert all(count == 1 for count in counts.values())


def test_routes_only_to_enabled_configured_backends_or_default():
    """Verify routed backends are enabled configured backends or the default backend."""
    data = _load_output()
    cfg = _load_config()
    allowed = {cfg["default_backend"]} | {b["name"] for b in cfg["backends"] if _is_enabled(b)}
    for row in data["routed_requests"]:
        assert row["backend"] in allowed, f"{row['request_id']} routed to disallowed backend {row['backend']}"


def test_disabled_backend_is_never_selected():
    """Verify the disabled deprecated-v1 backend is excluded even when headers match."""
    data = _load_output()
    disabled_hits = [r for r in data["routed_requests"] if r["backend"] == DISABLED_BACKEND]
    assert disabled_hits == []
    assert DISABLED_BACKEND not in data["summary"]["backend_counts"] or data["summary"]["backend_counts"][DISABLED_BACKEND] == 0


def test_backend_counts_match_routed_requests():
    """Verify summary.backend_counts is recomputed from routed_requests exactly."""
    data = _load_output()
    actual = Counter(row["backend"] for row in data["routed_requests"])
    assert data["summary"]["backend_counts"] == dict(actual) or all(
        data["summary"]["backend_counts"].get(k, 0) == v for k, v in actual.items()
    )


def test_expected_weights_report_enabled_config_weights():
    """Verify expected_weights reports raw configured weights for enabled backends only."""
    cfg = _load_config()
    expected = {b["name"]: b["weight"] for b in cfg["backends"] if _is_enabled(b)}
    assert _load_output()["summary"]["expected_weights"] == expected


def test_no_fallback_for_supplied_requests():
    """Verify the supplied request fixture is fully covered by enabled backend rules."""
    counts = _load_output()["summary"]["backend_counts"]
    assert counts.get(FALLBACK_BACKEND, 0) == 0


def test_header_matched_requests_do_not_cross_route_between_canaries():
    """Verify v2 and v3 canary headers do not route to the wrong canary backend."""
    data = _load_output()
    routed = {rid: row["backend"] for rid, row in ((r["request_id"], r) for r in data["routed_requests"])}
    for req in _load_requests():
        headers = req["headers"]
        if headers.get("x-canary") == "enabled":
            assert routed[req["id"]] != AUTHORIZED_BACKEND
        if headers.get("x-canary") == "v3":
            assert routed[req["id"]] != ENABLED_BACKEND


def test_case_insensitive_header_names_enable_canary_v2():
    """Verify lowercase request header names can match mixed-case rule header names."""
    data = _load_output()
    reqs = _load_requests()
    enabled_requests = [r for r in reqs if r["headers"].get("x-canary") == "enabled"]
    assert enabled_requests, "fixture must contain enabled canary requests"
    v2_hits = sum(1 for row in data["routed_requests"] if row["backend"] == ENABLED_BACKEND)
    assert v2_hits >= max(1, len(enabled_requests) // 6), "canary-v2 received too little traffic for matching headers"


def test_v3_requires_authorization_token():
    """Verify x-canary:v3 without the configured bearer token never routes to canary-v3."""
    data = _load_output()
    routed = {row["request_id"]: row["backend"] for row in data["routed_requests"]}
    unauthorized = [
        req for req in _load_requests()
        if req["headers"].get("x-canary") == "v3" and req["headers"].get("authorization") != BEARER_TOKEN
    ]
    assert unauthorized, "fixture must contain unauthorized v3 requests"
    for req in unauthorized:
        assert routed[req["id"]] != AUTHORIZED_BACKEND


# ---- Rebuild and rerun behavior ----


def test_binary_was_rebuilt_from_go_sources():
    """Verify /app/bin/splitter is an ELF binary newer than edited Go source files."""
    assert BINARY_PATH.is_file(), f"binary missing at {BINARY_PATH}"
    with BINARY_PATH.open("rb") as f:
        assert f.read(4) == b"\x7fELF"
    bin_mtime = BINARY_PATH.stat().st_mtime
    go_files = list(SPLITTER_DIR.rglob("*.go"))
    assert go_files, "no Go source files found"
    for path in go_files:
        assert bin_mtime >= path.stat().st_mtime, f"binary is older than {path}"


def test_binary_rerun_is_valid_and_overwrites_output():
    """Verify the rebuilt binary can rerun successfully and regenerate valid output."""
    result = run([str(BINARY_PATH)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    data = _load_output()
    assert len(data["routed_requests"]) == len(_load_requests())
    assert data["summary"]["total_requests"] == len(_load_requests())


def test_seeded_rerun_preserves_disabled_and_fallback_contracts():
    """Verify a deterministic rerun still excludes disabled and fallback backends."""
    env = dict(os.environ)
    env["SEED"] = "2"
    result = run([str(BINARY_PATH)], env=env, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    counts = _load_output()["summary"]["backend_counts"]
    assert counts.get(DISABLED_BACKEND, 0) == 0
    assert counts.get(FALLBACK_BACKEND, 0) == 0
    assert counts.get(ENABLED_BACKEND, 0) > 0
    assert counts.get(STABLE_BACKEND, 0) > 0


# ---- Extra behavioral contract tests using fresh Go fixtures ----


def test_go_contract_handles_disabled_backends_v3_auth_and_raw_weights(tmp_path):
    """Run Go-level behavioral tests against custom configs not present in the main fixture."""
    test_file = SPLITTER_DIR / "splitter" / "routing_contract_extra_test.go"
    test_file.write_text(r'''
package splitter

import (
    "math/rand"
    "testing"

    "github.com/terminal-bench/splitter/models"
)

func boolPtr(v bool) *bool { return &v }

func TestExtraDisabledBackendNeverWins(t *testing.T) {
    cfg := &models.SplitConfig{DefaultBackend: "fallback", Backends: []models.BackendRule{
        {Name: "disabled-trap", Weight: 999, Enabled: boolPtr(false), Headers: []models.HeaderMatch{{Name: "X-Canary", Value: "enabled"}}},
        {Name: "canary", Weight: 1, Headers: []models.HeaderMatch{{Name: "X-Canary", Value: "enabled"}}},
        {Name: "stable", Weight: 1},
    }}
    reqs := make([]models.Request, 60)
    for i := range reqs {
        reqs[i] = models.Request{ID: "enabled", Headers: map[string]string{"x-canary": "enabled"}}
    }
    got, _ := RouteRequests(reqs, cfg, 13)
    for _, row := range got {
        if row.Backend == "disabled-trap" { t.Fatalf("disabled backend was selected: %+v", row) }
    }
}

func TestExtraAuthorizedV3CanWinAndWrongAuthFallsBack(t *testing.T) {
    cfg := &models.SplitConfig{DefaultBackend: "fallback", Backends: []models.BackendRule{
        {Name: "canary-v3", Weight: 100, Headers: []models.HeaderMatch{{Name: "X-Canary", Value: "v3"}, {Name: "Authorization", Value: "Bearer test-token"}}},
        {Name: "stable", Weight: 0},
    }}
    reqs := []models.Request{
        {ID: "ok", Headers: map[string]string{"x-canary": "v3", "authorization": "Bearer test-token"}},
        {ID: "bad", Headers: map[string]string{"x-canary": "v3", "authorization": "Bearer wrong-token"}},
    }
    got, _ := RouteRequests(reqs, cfg, 9)
    if got[0].Backend != "canary-v3" || got[0].RuleName != "canary-v3" { t.Fatalf("authorized v3 did not route to canary-v3: %+v", got[0]) }
    if got[1].Backend != "fallback" || got[1].RuleName != "default" { t.Fatalf("wrong auth should fall back when no enabled candidate remains: %+v", got[1]) }
}

func TestExtraRawWeightSequenceMatchesReference(t *testing.T) {
    cfg := &models.SplitConfig{DefaultBackend: "fallback", Backends: []models.BackendRule{
        {Name: "a", Weight: 1}, {Name: "b", Weight: 2}, {Name: "c", Weight: 5},
    }}
    reqs := make([]models.Request, 40)
    for i := range reqs { reqs[i] = models.Request{ID: "r", Headers: map[string]string{}} }
    got, _ := RouteRequests(reqs, cfg, 7)
    rng := rand.New(rand.NewSource(7))
    for i := range reqs {
        // reproduce the contract directly with raw total weight 8
        roll := rng.Intn(8)
        want := "c"
        if roll < 1 { want = "a" } else if roll < 3 { want = "b" }
        if got[i].Backend != want { t.Fatalf("request %d: got %s want %s for roll %d", i, got[i].Backend, want, roll) }
    }
}
''')
    try:
        result = run(["go", "test", "./..."], cwd=SPLITTER_DIR, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        try:
            test_file.unlink()
        except FileNotFoundError:
            pass


def test_go_contract_handles_token_and_absent_header_modes(tmp_path):
    """Run Go-level tests for token-list and absent-header match modes using fresh fixtures."""
    test_file = SPLITTER_DIR / "splitter" / "routing_contract_modes_test.go"
    test_file.write_text(r"""
package splitter

import (
    "testing"

    "github.com/terminal-bench/splitter/models"
)

func TestExtraContainsTokenModeTrimsCommaSeparatedHeaderValues(t *testing.T) {
    cfg := &models.SplitConfig{DefaultBackend: "fallback", Backends: []models.BackendRule{
        {Name: "regional-eu", Weight: 100, Headers: []models.HeaderMatch{{Name: "X-Region-List", Value: "eu-west", Mode: "contains-token"}}},
    }}
    reqs := []models.Request{
        {ID: "token-ok", Headers: map[string]string{"x-region-list": "us-east, eu-west ,ap-south"}},
        {ID: "token-substring-no", Headers: map[string]string{"X-Region-List": "eu-west-1,ap-south"}},
    }
    got, _ := RouteRequests(reqs, cfg, 21)
    if got[0].Backend != "regional-eu" || got[0].RuleName != "regional-eu" { t.Fatalf("token match did not select regional backend: %+v", got[0]) }
    if got[1].Backend != "fallback" || got[1].RuleName != "default" { t.Fatalf("contains-token must not accept substrings: %+v", got[1]) }
}

func TestExtraAbsentModeTreatsEmptyHeaderAsPresent(t *testing.T) {
    cfg := &models.SplitConfig{DefaultBackend: "fallback", Backends: []models.BackendRule{
        {Name: "clean-regional", Weight: 100, Headers: []models.HeaderMatch{{Name: "X-Region-List", Value: "eu-west", Mode: "contains-token"}, {Name: "X-Debug", Mode: "absent"}}},
    }}
    reqs := []models.Request{
        {ID: "clean", Headers: map[string]string{"x-region-list": "eu-west,us-east"}},
        {ID: "debug", Headers: map[string]string{"x-region-list": "eu-west", "x-debug": ""}},
    }
    got, _ := RouteRequests(reqs, cfg, 22)
    if got[0].Backend != "clean-regional" { t.Fatalf("absent mode should allow requests without the header: %+v", got[0]) }
    if got[1].Backend != "fallback" || got[1].RuleName != "default" { t.Fatalf("empty debug header is still present and should block the rule: %+v", got[1]) }
}
""")
    try:
        result = run(["go", "test", "./..."], cwd=SPLITTER_DIR, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stdout + result.stderr
    finally:
        try:
            test_file.unlink()
        except FileNotFoundError:
            pass


# ---- Anti-cheat and consistency checks ----


def test_output_is_not_static_or_handwritten_shape_only():
    """Verify output contains real per-request routes and no unknown rule names."""
    data = _load_output()
    allowed_rules = {"default"} | {b["name"] for b in _load_config()["backends"] if _is_enabled(b)}
    assert data["routed_requests"], "routed_requests is empty"
    for row in data["routed_requests"]:
        assert row["rule_name"] in allowed_rules
        if row["backend"] != FALLBACK_BACKEND:
            assert row["rule_name"] == row["backend"]


def test_backend_counts_sum_matches_total_requests():
    """Verify all backend count values add up to summary.total_requests."""
    data = _load_output()
    assert sum(data["summary"]["backend_counts"].values()) == data["summary"]["total_requests"]
