"""Milestone 3 tests for StampGate JWS replay audit report."""
import json
import os
import sqlite3
import subprocess

import jsonschema
import pytest

from audit_reference import (
    API_BASE,
    AUDIT_DECISIONS,
    NONCE_DB,
    REPORT_REJECTED_COUNT,
    REPORT_REPLAY_COUNT,
    REPORT_VALID_COUNT,
    VALID_REPLAY_COUNT,
    WORKSPACE,
    expected_audit_report,
    load_json,
    nonce_row_count,
    output_path,
)

POLICY_PATH = output_path("policy-cache.json")
REPORT_PATH = output_path("jws-audit-report.json")
SCHEMA_PATH = os.path.join(WORKSPACE, "schemas", "jws-audit-report.schema.json")
REPORT_CMD = [
    "ruby",
    "/workspace/stampgate-lib/bin/stampgate-audit",
    "report",
    "--api",
    API_BASE,
    "--ledger",
    "/workspace/data/assertion-ledger.csv",
    "--policy",
    POLICY_PATH,
    "--cache",
    str(NONCE_DB),
    "--out",
    REPORT_PATH,
]


@pytest.fixture(scope="module")
def report_doc():
    """Load jws-audit-report.json from the workspace output directory."""
    assert os.path.isfile(REPORT_PATH), f"Missing {REPORT_PATH}"
    return load_json(REPORT_PATH)


class TestMilestone3:
    def test_m3_report_exits_zero(self):
        """Report subcommand must succeed with policy cache and nonce db."""
        run = subprocess.run(
            REPORT_CMD,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert run.returncode == 0, run.stderr

    def test_m3_schema_valid(self, report_doc):
        """Audit report must validate against its schema."""
        with open(SCHEMA_PATH, encoding="utf-8") as handle:
            schema = json.load(handle)
        jsonschema.validate(report_doc, schema)

    def test_m3_decisions_match_reference(self, report_doc):
        """Each final decision must match the reference replay audit."""
        expected = expected_audit_report(
            POLICY_PATH,
            "/workspace/data/assertion-ledger.csv",
            str(NONCE_DB),
        )
        for actual, ref in zip(report_doc["events"], expected["events"], strict=True):
            assert actual == ref

    def test_m3_asrt007_replay(self, report_doc):
        """asrt-007 must be replay after acme-lab reuses asrt-001 jti."""
        row = next(r for r in report_doc["events"] if r["assertion_id"] == "asrt-007")
        assert row["decision"] == "replay"

    def test_m3_asrt001_valid(self, report_doc):
        """asrt-001 must be valid on first use."""
        row = next(r for r in report_doc["events"] if r["assertion_id"] == "asrt-001")
        assert row["decision"] == "valid"

    def test_m3_decision_table(self, report_doc):
        """Spot check documented final decision table."""
        by_id = {row["assertion_id"]: row["decision"] for row in report_doc["events"]}
        assert by_id == AUDIT_DECISIONS

    def test_m3_nonce_cache_rows(self):
        """Sixteen valid assertions must be recorded in nonce_seen."""
        assert nonce_row_count() == VALID_REPLAY_COUNT

    def test_m3_summary_counts(self, report_doc):
        """Report must include valid, replay, and rejected summary integers."""
        assert report_doc["valid_count"] == REPORT_VALID_COUNT
        assert report_doc["replay_count"] == REPORT_REPLAY_COUNT
        assert report_doc["rejected_count"] == REPORT_REJECTED_COUNT

    def test_m3_asrt019_foxtrot_replay(self, report_doc):
        """asrt-019 must be replay after foxtrot reuses asrt-018 jti."""
        row = next(r for r in report_doc["events"] if r["assertion_id"] == "asrt-019")
        assert row["decision"] == "replay"
        assert "matched_iat" in row

    def test_m3_asrt023_india_replay(self, report_doc):
        """asrt-023 must be replay after india reuses asrt-020 jti."""
        row = next(r for r in report_doc["events"] if r["assertion_id"] == "asrt-023")
        assert row["decision"] == "replay"

    def test_m3_asrt021_invalid_jti(self, report_doc):
        """asrt-021 must be invalid_jti in the final audit report."""
        row = next(r for r in report_doc["events"] if r["assertion_id"] == "asrt-021")
        assert row["decision"] == "invalid_jti"

    def test_m3_asrt034_iss_mismatch(self, report_doc):
        """asrt-034 must be invalid_signature when payload iss names the wrong issuer."""
        row = next(r for r in report_doc["events"] if r["assertion_id"] == "asrt-034")
        assert row["decision"] == "invalid_signature"

    def test_m3_asrt032_valid_boundary(self, report_doc):
        """asrt-032 must be valid on the inclusive default skew boundary."""
        row = next(r for r in report_doc["events"] if r["assertion_id"] == "asrt-032")
        assert row["decision"] == "valid"

    def test_m3_replay_rows_include_matched_iat(self, report_doc):
        """Replay rows must still echo matched_iat."""
        for assertion_id in ("asrt-007", "asrt-017", "asrt-019", "asrt-023"):
            row = next(r for r in report_doc["events"] if r["assertion_id"] == assertion_id)
            assert "matched_iat" in row

    def test_m3_asrt013_alg_mismatch(self, report_doc):
        """asrt-013 must be alg_mismatch for bravo header alg ES256."""
        row = next(r for r in report_doc["events"] if r["assertion_id"] == "asrt-013")
        assert row["decision"] == "alg_mismatch"

    def test_m3_asrt011_outside_skew(self, report_doc):
        """asrt-011 must be outside_skew for echo require_exact_iat flag."""
        row = next(r for r in report_doc["events"] if r["assertion_id"] == "asrt-011")
        assert row["decision"] == "outside_skew"

    def test_m3_nonce_cache_tuple(self):
        """Nonce table must store acme-lab asrt-001 tuple with assertion_id."""
        conn = sqlite3.connect(NONCE_DB)
        row = conn.execute(
            "SELECT assertion_id, recorded_at FROM nonce_seen WHERE issuer = ? AND jti = ?",
            ("acme-lab", "jti-acme-001"),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == "asrt-001"

    def test_m3_nonce_recorded_at(self):
        """recorded_at must equal observed_at_utc from the accepted ledger row."""
        conn = sqlite3.connect(NONCE_DB)
        row = conn.execute(
            "SELECT recorded_at FROM nonce_seen WHERE assertion_id = ?",
            ("asrt-020",),
        ).fetchone()
        conn.close()
        assert row is not None
        assert row[0] == 1718487000

    def test_m3_nonce_schema_columns(self):
        """nonce_seen must keep all five columns from nonce-schema.sql."""
        conn = sqlite3.connect(NONCE_DB)
        columns = [item[1] for item in conn.execute("PRAGMA table_info(nonce_seen)")]
        conn.close()
        assert columns == ["issuer", "jti", "alg", "assertion_id", "recorded_at"]

    def test_m3_rerun_detects_replay(self):
        """Re-running report on a fresh copy must still mark asrt-007 replay."""
        backup = NONCE_DB.read_bytes()
        try:
            conn = sqlite3.connect(NONCE_DB)
            conn.execute("DELETE FROM nonce_seen")
            conn.commit()
            conn.close()
            run = subprocess.run(
                REPORT_CMD,
                cwd=WORKSPACE,
                capture_output=True,
                text=True,
                timeout=120,
            )
            assert run.returncode == 0, run.stderr
            doc = load_json(REPORT_PATH)
            row = next(r for r in doc["events"] if r["assertion_id"] == "asrt-007")
            assert row["decision"] == "replay"
        finally:
            NONCE_DB.write_bytes(backup)

    def test_m3_cache_path_field(self, report_doc):
        """Report must echo the nonce cache path argument."""
        assert report_doc["cache_path"] == str(NONCE_DB)

    def test_m3_skip_nonce_clear_rejects(self):
        """Report must reject STAMPGATE_SKIP_NONCE_CLEAR before nonce work."""
        env = os.environ.copy()
        env["STAMPGATE_SKIP_NONCE_CLEAR"] = "1"
        run = subprocess.run(
            REPORT_CMD,
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        assert run.returncode != 0
        assert "nonce clear bypass disabled" in run.stderr
