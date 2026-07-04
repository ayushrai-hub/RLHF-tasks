"""ABAC framed-wire constraint auditor — ingest, replay, export, and HTTP probe verifier."""

from __future__ import annotations

import sqlite3
import subprocess

from abac_expect import (
    assert_report_matches_db,
    expected_audit_hash,
    top_level_key_order,
)
from abac_harness import (
    ABAC_BAD_CRC_BATCH,
    ABAC_DENY_TRAP_BATCH,
    ABAC_DUP_SEQ_BATCH,
    ABAC_GOOD_BATCH,
    ABAC_MISSING_ATTR_BATCH,
    ABAC_OOO_BATCH,
    EXPORT_BIN,
    INGEST_BIN,
    PUBLIC_SAMPLE,
    SERVE_BIN,
    abac_cli_export,
    abac_cli_ingest,
    abac_parse_report,
    abac_wire_batch,
    http_get_json,
    http_post_json,
    start_abac_http,
)

_ABAC_TOP_KEYS = [
    "tenant_id",
    "batch_id",
    "reported_at_unix",
    "decisions",
    "stats",
    "audit_hash",
]
_EPOCH_BASE = 1700000000


def test_abac_binaries_exist():
    """Prebuilt CLIs and HTTP server entrypoints must be present under /app/bin."""
    for path in (INGEST_BIN, EXPORT_BIN, SERVE_BIN):
        assert path.is_file() and path.stat().st_size > 0


def test_public_sample_ingest_export_smoke(tmp_path):
    """Public warmup cartridge ingests and exports schema-shaped audit JSON."""
    db = tmp_path / "smoke.db"
    out = tmp_path / "smoke.json"
    assert abac_cli_ingest(db, PUBLIC_SAMPLE).returncode == 0
    assert abac_cli_export(db, out).returncode == 0
    report = abac_parse_report(out)
    assert report["tenant_id"] == "TEN"
    assert report["batch_id"] == "sample-abac-01"
    assert len(report["audit_hash"]) == 64


def test_export_top_level_key_order(tmp_path):
    """Written audit JSON must follow audit-report-schema top-level field order."""
    db = tmp_path / "order.db"
    out = tmp_path / "order.json"
    abac_cli_ingest(db, PUBLIC_SAMPLE)
    abac_cli_export(db, out)
    assert top_level_key_order(abac_parse_report(out)) == _ABAC_TOP_KEYS


def test_reported_at_uses_epoch_base(tmp_path):
    """reported_at_unix must be abac_epoch_base plus max utc_offset_sec for tenant."""
    db = tmp_path / "epoch.db"
    out = tmp_path / "epoch.json"
    abac_cli_ingest(db, PUBLIC_SAMPLE)
    abac_cli_export(db, out)
    report = abac_parse_report(out)
    assert report["reported_at_unix"] == _EPOCH_BASE + 200


def test_public_deny_overrides_effective_decision(tmp_path):
    """Deny-overrides combiner must leave access policy effective_decision at 0."""
    db = tmp_path / "deny.db"
    out = tmp_path / "deny.json"
    abac_cli_ingest(db, PUBLIC_SAMPLE)
    abac_cli_export(db, out)
    report = abac_parse_report(out)
    access = next(d for d in report["decisions"] if d["policy_id"] == "access")
    assert access["effective_decision"] == 0
    assert access["last_eval_seq"] == 2
    assert report["stats"]["denies_overridden"] == 1
    assert report["stats"]["evals_applied"] == 2


def test_audit_hash_matches_expect(tmp_path):
    """Export audit_hash must match independent SHA-256 payload from SQLite."""
    db = tmp_path / "hash.db"
    out = tmp_path / "hash.json"
    abac_cli_ingest(db, PUBLIC_SAMPLE)
    abac_cli_export(db, out)
    report = abac_parse_report(out)
    conn = sqlite3.connect(db)
    try:
        assert report["audit_hash"] == expected_audit_hash(conn, "TEN")
    finally:
        conn.close()


def test_assert_report_matches_db_public(tmp_path):
    """Full export report must match abac_expect replay of persisted ledger rows."""
    db = tmp_path / "expect.db"
    out = tmp_path / "expect.json"
    abac_cli_ingest(db, PUBLIC_SAMPLE)
    abac_cli_export(db, out)
    assert_report_matches_db(abac_parse_report(out), db, "TEN")


def test_hidden_good_crc_ingest(tmp_path):
    """ABWF cartridges with CRC over post-magic body through batch_id must ingest."""
    # tests/fixtures/ good_crc.abwf — CRC scope excludes ABWF magic prefix
    db = tmp_path / "good.db"
    out = tmp_path / "good.json"
    assert abac_cli_ingest(db, abac_wire_batch(ABAC_GOOD_BATCH)).returncode == 0
    abac_cli_export(db, out)
    report = abac_parse_report(out)
    assert report["stats"]["evals_applied"] == 2


def test_bad_crc_rejects_ingest(tmp_path):
    """Footer CRC mismatch must fail ingest without committing partial events."""
    # tests/fixtures/ bad_crc.abwf mutated footer
    db = tmp_path / "bad.db"
    rc = abac_cli_ingest(db, abac_wire_batch(ABAC_BAD_CRC_BATCH)).returncode
    assert rc != 0
    conn = sqlite3.connect(db)
    try:
        count = conn.execute("SELECT COUNT(*) FROM abac_eval_events").fetchone()[0]
        assert count == 0
    finally:
        conn.close()


def test_out_of_order_eval_seq_replay_order(tmp_path):
    """Physical file order must not override ascending eval_seq replay."""
    db = tmp_path / "ooo.db"
    out = tmp_path / "ooo.json"
    abac_cli_ingest(db, abac_wire_batch(ABAC_OOO_BATCH))
    abac_cli_export(db, out)
    report = abac_parse_report(out)
    access = next(d for d in report["decisions"] if d["policy_id"] == "access")
    assert access["effective_decision"] == 0
    assert report["stats"]["denies_overridden"] == 1


def test_missing_clearance_fail_closed(tmp_path):
    """Missing required clearance attribute must increment missing_attr_rejected."""
    db = tmp_path / "miss.db"
    out = tmp_path / "miss.json"
    abac_cli_ingest(db, abac_wire_batch(ABAC_MISSING_ATTR_BATCH))
    abac_cli_export(db, out)
    report = abac_parse_report(out)
    assert report["stats"]["missing_attr_rejected"] >= 1
    assert report["stats"]["evals_applied"] == 0


def test_duplicate_eval_seq_skipped(tmp_path):
    """Duplicate tenant eval_seq within a batch must increment duplicate_skipped."""
    db = tmp_path / "dup.db"
    out = tmp_path / "dup.json"
    abac_cli_ingest(db, abac_wire_batch(ABAC_DUP_SEQ_BATCH))
    abac_cli_export(db, out)
    report = abac_parse_report(out)
    assert report["stats"]["duplicate_skipped"] >= 1
    assert report["stats"]["evals_applied"] == 1


def test_deny_only_after_permit_combiner(tmp_path):
    """Later deny eval must override earlier permit for the same policy_id."""
    db = tmp_path / "trap.db"
    out = tmp_path / "trap.json"
    abac_cli_ingest(db, abac_wire_batch(ABAC_DENY_TRAP_BATCH))
    abac_cli_export(db, out)
    report = abac_parse_report(out)
    px = next(d for d in report["decisions"] if d["policy_id"] == "policy-x")
    assert px["effective_decision"] == 0
    assert report["stats"]["denies_overridden"] == 1


def test_idempotent_batch_reingest(tmp_path):
    """Identical batch bytes must not double-apply eval events on re-ingest."""
    db = tmp_path / "idem.db"
    out = tmp_path / "idem.json"
    batch = abac_wire_batch(ABAC_GOOD_BATCH)
    assert abac_cli_ingest(db, batch).returncode == 0
    assert abac_cli_ingest(db, batch).returncode == 0
    abac_cli_export(db, out)
    report = abac_parse_report(out)
    assert report["stats"]["evals_applied"] == 2
    assert report["stats"]["duplicate_skipped"] == 0


def test_empty_db_export_schema(tmp_path):
    """Export on empty SQLite must emit empty decisions, zero stats, and valid audit_hash."""
    db = tmp_path / "empty.db"
    out = tmp_path / "empty.json"
    sqlite3.connect(db).close()
    assert abac_cli_export(db, out).returncode == 0
    report = abac_parse_report(out)
    assert report["batch_id"] == ""
    assert report["decisions"] == []
    assert report["stats"] == {
        "evals_applied": 0,
        "denies_overridden": 0,
        "missing_attr_rejected": 0,
        "duplicate_skipped": 0,
    }
    assert report["reported_at_unix"] == _EPOCH_BASE
    assert_report_matches_db(report, db, "TEN")


def test_multi_policy_decisions_sorted(tmp_path):
    """decisions[] must be sorted by policy_id in export JSON."""
    db = tmp_path / "multi.db"
    out = tmp_path / "multi.json"
    abac_cli_ingest(db, PUBLIC_SAMPLE)
    abac_cli_ingest(db, abac_wire_batch(ABAC_DENY_TRAP_BATCH))
    abac_cli_export(db, out)
    ids = [d["policy_id"] for d in abac_parse_report(out)["decisions"]]
    assert ids == sorted(ids)


class TestAbacPartialFixCanaries:
    """Behaviors that fail when only one ABAC subsystem is repaired."""

    def test_partial_fix_crc_body_excludes_magic_prefix(self, tmp_path):
        """CRC scope starts after ABWF magic through batch_id inclusive."""
        db = tmp_path / "pf_crc.db"
        assert abac_cli_ingest(db, abac_wire_batch(ABAC_GOOD_BATCH)).returncode == 0

    def test_partial_fix_replay_sorts_eval_seq(self, tmp_path):
        """Out-of-order cartridge bytes must replay by eval_seq not file order."""
        db = tmp_path / "pf_sort.db"
        out = tmp_path / "pf_sort.json"
        abac_cli_ingest(db, abac_wire_batch(ABAC_OOO_BATCH))
        abac_cli_export(db, out)
        assert abac_parse_report(out)["stats"]["denies_overridden"] == 1

    def test_partial_fix_store_load_events_by_eval_seq(self, tmp_path):
        """SQLite reload must order events by eval_seq not rowid."""
        db = tmp_path / "pf_store.db"
        out = tmp_path / "pf_store.json"
        abac_cli_ingest(db, PUBLIC_SAMPLE)
        abac_cli_export(db, out)
        access = next(
            d for d in abac_parse_report(out)["decisions"] if d["policy_id"] == "access"
        )
        assert access["last_eval_seq"] == 2

    def test_partial_fix_deny_overrides_without_permit_first(self, tmp_path):
        """Deny-overrides combiner must force effective 0 after permit then deny."""
        db = tmp_path / "pf_comb.db"
        out = tmp_path / "pf_comb.json"
        abac_cli_ingest(db, abac_wire_batch(ABAC_DENY_TRAP_BATCH))
        abac_cli_export(db, out)
        report = abac_parse_report(out)
        assert report["decisions"][0]["effective_decision"] == 0

    def test_partial_fix_fail_closed_required_attrs(self, tmp_path):
        """Required attribute binding must reject evals missing clearance."""
        db = tmp_path / "pf_attr.db"
        out = tmp_path / "pf_attr.json"
        abac_cli_ingest(db, abac_wire_batch(ABAC_MISSING_ATTR_BATCH))
        abac_cli_export(db, out)
        assert abac_parse_report(out)["stats"]["missing_attr_rejected"] >= 1

    def test_partial_fix_canonical_hash_tenant_batch_order(self, tmp_path):
        """audit_hash payload must use tenant_id before batch_id segment."""
        db = tmp_path / "pf_hash.db"
        out = tmp_path / "pf_hash.json"
        abac_cli_ingest(db, PUBLIC_SAMPLE)
        abac_cli_export(db, out)
        assert_report_matches_db(abac_parse_report(out), db, "TEN")

    def test_partial_fix_export_epoch_not_wall_clock(self, tmp_path):
        """reported_at_unix must track profile epoch plus max utc_offset_sec."""
        db = tmp_path / "pf_epoch.db"
        out = tmp_path / "pf_epoch.json"
        abac_cli_ingest(db, PUBLIC_SAMPLE)
        abac_cli_export(db, out)
        assert abac_parse_report(out)["reported_at_unix"] == _EPOCH_BASE + 200

    def test_partial_fix_tenant_stats_scoped_empty_export(self, tmp_path):
        """Empty-batch duplicate_skipped must use tenant counter not global rollup."""
        db = tmp_path / "pf_tdup.db"
        out = tmp_path / "pf_tdup.json"
        abac_cli_ingest(db, abac_wire_batch(ABAC_DUP_SEQ_BATCH))
        assert abac_cli_export(db, out, tenant="NOPE").returncode == 0
        report = abac_parse_report(out)
        assert report["batch_id"] == ""
        assert report["stats"]["duplicate_skipped"] == 0

    def test_partial_fix_probe_merge_coordinator_snapshots(self, tmp_path):
        """ProbeMergeCoordinator must load SQLite snapshots when body omits attrs."""
        db = tmp_path / "pf_merge.db"
        abac_cli_ingest(db, PUBLIC_SAMPLE)
        with start_abac_http(db, 19104) as port:
            status, body = http_post_json(
                f"http://127.0.0.1:{port}/v1/tenants/TEN/probe",
                {"policy_id": "access"},
            )
            assert status == 200
            assert body.get("effective_decision") == 1


class TestAbacHttpCoupling:
    """HTTP probe routes must stay consistent with CLI ingest and SQLite snapshots."""

    def test_coupling_health_before_probe(self, tmp_path):
        """GET /health must succeed before probe routes are exercised."""
        db = tmp_path / "c_health.db"
        with start_abac_http(db, 19101) as port:
            status, body = http_get_json(f"http://127.0.0.1:{port}/health")
            assert status == 200
            assert body.get("status") == "ok"

    def test_coupling_probe_fail_closed_empty_db(self, tmp_path):
        """Probe with only policy_id on empty DB must fail-closed to effective 0."""
        db = tmp_path / "c_empty.db"
        sqlite3.connect(db).close()
        with start_abac_http(db, 19102) as port:
            status, body = http_post_json(
                f"http://127.0.0.1:{port}/v1/tenants/TEN/probe",
                {"policy_id": "access"},
            )
            assert status == 200
            assert body.get("effective_decision") == 0

    def test_coupling_probe_uses_snapshots_after_ingest(self, tmp_path):
        """Probe must merge persisted attribute snapshots when body omits attrs."""
        db = tmp_path / "c_snap.db"
        abac_cli_ingest(db, PUBLIC_SAMPLE)
        with start_abac_http(db, 19103) as port:
            status, body = http_post_json(
                f"http://127.0.0.1:{port}/v1/tenants/TEN/probe",
                {"policy_id": "access"},
            )
            assert status == 200
            assert body.get("effective_decision") == 1

    def test_coupling_export_matches_db_after_ingest(self, tmp_path):
        """CLI export audit_hash must match independent expect after ingest."""
        db = tmp_path / "c_exp.db"
        out = tmp_path / "c_exp.json"
        abac_cli_ingest(db, abac_wire_batch(ABAC_GOOD_BATCH))
        abac_cli_export(db, out)
        assert_report_matches_db(abac_parse_report(out), db, "TEN")


class TestAbacIntegration:
    """Cross-subsystem scenarios requiring ingest, internal replay, and export."""

    def test_integration_unknown_tenant_empty_export(self, tmp_path):
        """Export for tenant with no batches uses empty batch_id and zero stats."""
        db = tmp_path / "i_unknown.db"
        out = tmp_path / "i_unknown.json"
        abac_cli_ingest(db, PUBLIC_SAMPLE)
        assert abac_cli_export(db, out, tenant="NOPE").returncode == 0
        report = abac_parse_report(out)
        assert report["tenant_id"] == "NOPE"
        assert report["batch_id"] == ""
        assert report["decisions"] == []
        assert report["stats"]["duplicate_skipped"] == 0
        assert_report_matches_db(report, db, "NOPE")

    def test_integration_sqlite_event_count_after_public_ingest(self, tmp_path):
        """Ingest must persist both eval rows and attribute pairs in SQLite."""
        db = tmp_path / "i_rows.db"
        abac_cli_ingest(db, PUBLIC_SAMPLE)
        conn = sqlite3.connect(db)
        try:
            ev_count = conn.execute(
                "SELECT COUNT(*) FROM abac_eval_events WHERE tenant_id='TEN'"
            ).fetchone()[0]
            attr_count = conn.execute("SELECT COUNT(*) FROM abac_eval_attrs").fetchone()[0]
            assert ev_count == 2
            assert attr_count >= 4
        finally:
            conn.close()

    def test_integration_build_check_only_skips_compile(self):
        """Verifier build gate must succeed without recompiling Scala sources."""
        proc = subprocess.run(
            ["/bin/bash", "/app/scripts/build.sh"],
            capture_output=True,
            text=True,
            env={"ABAC_BUILD_CHECK": "1", "PATH": "/app/bin:/opt/scala3/bin:/usr/bin:/bin"},
            timeout=30,
        )
        assert proc.returncode == 0
