"""Milestone 2 tests for StampGate JWS window verification."""
import json
import os
import sqlite3
import subprocess

import jsonschema
import pytest

from audit_reference import (
    API_BASE,
    NONCE_DB,
    WINDOW_DECISIONS,
    WORKSPACE,
    expected_window_check,
    load_json,
    nonce_row_count,
    output_path,
)

POLICY_PATH = output_path("policy-cache.json")
WINDOW_PATH = output_path("jws-window-check.json")
SCHEMA_PATH = os.path.join(WORKSPACE, "schemas", "jws-window-check.schema.json")
VERIFY_CMD = [
    "ruby",
    "/workspace/stampgate-lib/bin/stampgate-audit",
    "verify",
    "--api",
    API_BASE,
    "--ledger",
    "/workspace/data/assertion-ledger.csv",
    "--policy",
    POLICY_PATH,
    "--out",
    WINDOW_PATH,
]


@pytest.fixture(scope="module")
def window_doc():
    """Load jws-window-check.json from the workspace output directory."""
    assert os.path.isfile(WINDOW_PATH), f"Missing {WINDOW_PATH}"
    return load_json(WINDOW_PATH)


class TestMilestone2:
    def test_m2_verify_exits_zero(self):
        """Verify subcommand must succeed when policy cache is present."""
        run = subprocess.run(
            VERIFY_CMD,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert run.returncode == 0, run.stderr

    def test_m2_schema_valid(self, window_doc):
        """Window check output must validate against its schema."""
        with open(SCHEMA_PATH, encoding="utf-8") as handle:
            schema = json.load(handle)
        jsonschema.validate(window_doc, schema)

    def test_m2_event_count(self, window_doc):
        """All ledger rows must appear in the window check."""
        assert len(window_doc["events"]) == 35

    def test_m2_sorted_assertion_ids(self, window_doc):
        """Events must be sorted by assertion_id ascending."""
        ids = [row["assertion_id"] for row in window_doc["events"]]
        assert ids == sorted(ids)

    def test_m2_decisions_match_reference(self, window_doc):
        """Each event decision must match the reference window audit."""
        expected = expected_window_check(POLICY_PATH, "/workspace/data/assertion-ledger.csv")
        for actual, ref in zip(window_doc["events"], expected["events"], strict=True):
            assert actual == ref

    def test_m2_asrt003_invalid_signature(self, window_doc):
        """asrt-003 must be invalid_signature for tampered detached JWS."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-003")
        assert row["decision"] == "invalid_signature"

    def test_m2_asrt005_revoked(self, window_doc):
        """asrt-005 must be revoked for charlie."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-005")
        assert row["decision"] == "revoked"

    def test_m2_asrt008_outside_skew(self, window_doc):
        """asrt-008 must be outside_skew for delta stale iat."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-008")
        assert row["decision"] == "outside_skew"

    def test_m2_asrt006_ops_extended_skew(self, window_doc):
        """asrt-006 must be valid_window for ops within 120 second skew."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-006")
        assert row["decision"] == "valid_window"

    def test_m2_asrt011_echo_exact_iat(self, window_doc):
        """asrt-011 must be outside_skew for echo require_exact_iat flag."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-011")
        assert row["decision"] == "outside_skew"

    def test_m2_asrt012_bravo_eddsa(self, window_doc):
        """asrt-012 must be valid_window for bravo EdDSA lowercase kid."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-012")
        assert row["decision"] == "valid_window"

    def test_m2_asrt002_acme_zero_skew(self, window_doc):
        """asrt-002 must be outside_skew for acme-lab zero skew override."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-002")
        assert row["decision"] == "outside_skew"

    def test_m2_matched_iat_asrt006(self, window_doc):
        """asrt-006 must echo matched_iat from the payload."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-006")
        assert row["matched_iat"] == row["observed_at_utc"]

    def test_m2_rejected_rows_omit_matched_iat(self, window_doc):
        """Rejected rows must not include matched_iat."""
        for assertion_id in (
            "asrt-002",
            "asrt-003",
            "asrt-005",
            "asrt-008",
            "asrt-011",
            "asrt-013",
            "asrt-021",
            "asrt-022",
            "asrt-026",
            "asrt-028",
            "asrt-030",
            "asrt-031",
            "asrt-033",
            "asrt-034",
            "asrt-037",
        ):
            row = next(r for r in window_doc["events"] if r["assertion_id"] == assertion_id)
            assert "matched_iat" not in row

    def test_m2_decision_table(self, window_doc):
        """Spot check documented decision table from audit-output-spec."""
        by_id = {row["assertion_id"]: row["decision"] for row in window_doc["events"]}
        assert by_id == WINDOW_DECISIONS

    def test_m2_asrt013_alg_mismatch(self, window_doc):
        """asrt-013 must be alg_mismatch for bravo header alg ES256."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-013")
        assert row["decision"] == "alg_mismatch"

    def test_m2_policy_cache_unchanged(self):
        """Milestone 2 work must not rewrite the policy cache artifact."""
        doc = load_json(POLICY_PATH)
        assert doc["issuer_count"] == 9
        assert doc["policy_sources"] == ["/api/policy", "/api/issuers"]

    def test_m2_verify_rejects_nonempty_nonce_cache(self):
        """Verify must fail when nonce_seen already contains rows."""
        backup = NONCE_DB.read_bytes()
        try:
            conn = sqlite3.connect(NONCE_DB)
            conn.execute(
                "INSERT INTO nonce_seen (issuer, jti, alg, assertion_id, recorded_at) "
                "VALUES ('acme-lab', 'seed-jti', 'RS256', 'seed-row', 0)"
            )
            conn.commit()
            conn.close()
            run = subprocess.run(
                VERIFY_CMD,
                cwd=WORKSPACE,
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert run.returncode != 0
            assert "nonce cache must be empty before verify" in run.stderr
        finally:
            NONCE_DB.write_bytes(backup)

    def test_m2_verify_leaves_nonce_cache_empty(self):
        """Verify subcommand must not insert nonce_seen rows."""
        before = nonce_row_count()
        run = subprocess.run(
            VERIFY_CMD,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert run.returncode == 0, run.stderr
        assert nonce_row_count() == before

    def test_m2_asrt020_india_es256(self, window_doc):
        """asrt-020 must be valid_window for india ES256 raw signature."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-020")
        assert row["decision"] == "valid_window"

    def test_m2_asrt021_invalid_jti(self, window_doc):
        """asrt-021 must be invalid_jti for short jti before signature verify."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-021")
        assert row["decision"] == "invalid_jti"

    def test_m2_asrt022_future_nbf(self, window_doc):
        """asrt-022 must be outside_skew when nbf exceeds observed_at_utc."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-022")
        assert row["decision"] == "outside_skew"

    def test_m2_asrt024_ops_future_iat(self, window_doc):
        """asrt-024 must be valid_window for ops within 120 second forward skew."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-024")
        assert row["decision"] == "valid_window"

    def test_m2_asrt025_delta_skew_boundary(self, window_doc):
        """asrt-025 must be valid_window for delta within 45 second skew override."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-025")
        assert row["decision"] == "valid_window"

    def test_m2_asrt026_delta_skew_exceeded(self, window_doc):
        """asrt-026 must be outside_skew when delta skew override is exceeded by one second."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-026")
        assert row["decision"] == "outside_skew"

    def test_m2_asrt028_bravo_wrong_kid_case(self, window_doc):
        """asrt-028 must be invalid_signature for uppercase bravo kid header."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-028")
        assert row["decision"] == "invalid_signature"

    def test_m2_asrt029_juliet_exact_iat(self, window_doc):
        """asrt-029 must be valid_window for juliet require_exact_iat match."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-029")
        assert row["decision"] == "valid_window"

    def test_m2_asrt030_juliet_exact_iat_fail(self, window_doc):
        """asrt-030 must be outside_skew when juliet iat differs from observed_at_utc."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-030")
        assert row["decision"] == "outside_skew"

    def test_m2_asrt031_golf_alg_mismatch(self, window_doc):
        """asrt-031 must be alg_mismatch when ledger alg disagrees with signed header alg."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-031")
        assert row["decision"] == "alg_mismatch"

    def test_m2_asrt032_foxtrot_skew_boundary(self, window_doc):
        """asrt-032 must be valid_window on the inclusive default skew boundary."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-032")
        assert row["decision"] == "valid_window"

    def test_m2_asrt033_foxtrot_skew_exceeded(self, window_doc):
        """asrt-033 must be outside_skew one second beyond the default skew limit."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-033")
        assert row["decision"] == "outside_skew"

    def test_m2_asrt034_iss_mismatch(self, window_doc):
        """asrt-034 must be invalid_signature when payload iss names the wrong issuer."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-034")
        assert row["decision"] == "invalid_signature"

    def test_m2_asrt036_ops_forward_boundary(self, window_doc):
        """asrt-036 must be valid_window on the inclusive ops forward skew boundary."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-036")
        assert row["decision"] == "valid_window"

    def test_m2_asrt037_ops_forward_exceeded(self, window_doc):
        """asrt-037 must be outside_skew one second beyond the ops forward skew limit."""
        row = next(r for r in window_doc["events"] if r["assertion_id"] == "asrt-037")
        assert row["decision"] == "outside_skew"

    def test_m2_skip_nonce_guard_rejects(self):
        """Verify must reject STAMPGATE_SKIP_NONCE_GUARD before ledger processing."""
        env = os.environ.copy()
        env["STAMPGATE_SKIP_NONCE_GUARD"] = "1"
        run = subprocess.run(
            VERIFY_CMD,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        assert run.returncode != 0
        assert "nonce guard bypass disabled" in run.stderr
