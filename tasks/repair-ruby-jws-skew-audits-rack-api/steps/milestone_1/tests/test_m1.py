"""Milestone 1 tests for StampGate policy cache."""
import json
import os
import subprocess

import jsonschema
import pytest

from audit_reference import API_BASE, WORKSPACE, expected_policy_cache, load_json, output_path, read_text

POLICY_PATH = output_path("policy-cache.json")
SCHEMA_PATH = os.path.join(WORKSPACE, "schemas", "policy-cache.schema.json")
POLICY_CMD = [
    "ruby",
    "/workspace/stampgate-lib/bin/stampgate-audit",
    "policy",
    "--api",
    API_BASE,
    "--out",
    POLICY_PATH,
]


@pytest.fixture(scope="module")
def policy_doc():
    """Load policy-cache.json from the workspace output directory."""
    assert os.path.isfile(POLICY_PATH), f"Missing {POLICY_PATH}"
    return load_json(POLICY_PATH)


class TestMilestone1:
    def test_m1_policy_command_exits_zero(self):
        """Policy subcommand must succeed against the StampGate API."""
        run = subprocess.run(
            POLICY_CMD,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert run.returncode == 0, run.stderr

    def test_m1_trailing_newline(self):
        """Policy cache JSON must end with a trailing newline."""
        with open(POLICY_PATH, "rb") as handle:
            raw = handle.read()
        assert raw.endswith(b"\n")

    def test_m1_schema_valid(self, policy_doc):
        """Policy cache must validate against the shipped schema."""
        with open(SCHEMA_PATH, encoding="utf-8") as handle:
            schema = json.load(handle)
        jsonschema.validate(policy_doc, schema)

    def test_m1_global_policy_fields(self, policy_doc):
        """Global policy must mirror the Rack /api/policy payload."""
        expected = expected_policy_cache()["global_policy"]
        assert policy_doc["global_policy"] == expected

    def test_m1_active_issuers(self, policy_doc):
        """Active issuers must list only non-revoked accounts sorted ascending."""
        assert policy_doc["active_issuers"] == [
            "acme-lab",
            "bravo",
            "delta",
            "echo",
            "foxtrot",
            "golf",
            "india",
            "juliet",
            "ops",
        ]

    def test_m1_revoked_issuers(self, policy_doc):
        """Revoked issuers must list charlie only."""
        assert policy_doc["revoked_issuers"] == ["charlie"]

    def test_m1_issuer_counts(self, policy_doc):
        """Policy cache must include active and revoked summary integers."""
        assert policy_doc["issuer_count"] == 9
        assert policy_doc["revoked_count"] == 1

    def test_m1_policy_sources(self, policy_doc):
        """Policy cache must record the live API routes consulted."""
        assert policy_doc["policy_sources"] == ["/api/policy", "/api/issuers"]

    def test_m1_skew_overrides(self, policy_doc):
        """acme-lab and ops must carry documented skew overrides."""
        assert policy_doc["issuer_overrides"] == {
            "acme-lab": {"max_clock_skew_sec": 0},
            "delta": {"max_clock_skew_sec": 45},
            "ops": {"max_clock_skew_sec": 120},
        }

    def test_m1_api_base_echo(self, policy_doc):
        """api_base must echo the CLI --api argument."""
        assert policy_doc["api_base"] == API_BASE

    def test_m1_two_space_indent(self):
        """Policy cache must use two space JSON indentation."""
        raw = read_text(POLICY_PATH)
        assert '\n  "schema_version"' in raw

    def test_m1_excludes_pending_hotel(self, policy_doc):
        """Pending issuer hotel must not appear in active or revoked lists."""
        assert "hotel" not in policy_doc["active_issuers"]
        assert "hotel" not in policy_doc["revoked_issuers"]

    def test_m1_no_extra_top_level_keys(self, policy_doc):
        """Policy cache must not include fields outside the published schema."""
        allowed = {
            "schema_version",
            "api_base",
            "global_policy",
            "active_issuers",
            "revoked_issuers",
            "issuer_overrides",
            "issuer_count",
            "revoked_count",
            "policy_sources",
        }
        assert set(policy_doc.keys()) == allowed

    def test_m1_static_policy_env_rejects(self):
        """Policy subcommand must reject STAMPGATE_USE_STATIC_POLICY before API work."""
        env = os.environ.copy()
        env["STAMPGATE_USE_STATIC_POLICY"] = "1"
        run = subprocess.run(
            POLICY_CMD,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        assert run.returncode != 0
        assert "static policy bypass disabled" in run.stderr
