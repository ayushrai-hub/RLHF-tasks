"""Verifier tests for neural-echo-forge."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from echo_reference import (
    build_outputs,
    digest_snapshot_bytes,
    export_from_snapshot,
    ingest_all,
)

APP = Path("/app")
BINARY = APP / "neural-echo-forge"
SESSIONS = APP / "data" / "sessions"
POLICY = APP / "data" / "policies" / "memory-policy.json"
SNAPSHOT_PATH = APP / "state" / "memory-snapshot.json"
STAGING_PATH = APP / "state" / "ingest-staging.json"
RECONCILE_PATH = APP / "state" / "reconcile-report.json"
RECORDS_PATH = APP / "output" / "memory-records.json"
INDEX_PATH = APP / "output" / "retrieval-index.json"
AUDIT_PATH = APP / "output" / "memory-audit.json"
HIDDEN_SESSIONS = Path("/tests/fixtures/hidden/sessions")
HIDDEN_POLICY = Path("/tests/fixtures/hidden/policies/memory-policy.json")
HIDDEN_POLICY_SPLIT = Path("/tests/fixtures/hidden/policies/memory-policy-split.json")
BASELINE_BACKUP = Path("/tmp/nef-baseline-backup")
POLICY_BACKUP = Path("/tmp/nef-policy-backup")
ADV_SEED_RAW = os.environ.get("NEF_ADV_SEED", str(uuid.uuid4()))
ADV_SEED = int(hashlib.sha256(ADV_SEED_RAW.encode()).hexdigest()[:8], 16)


def _rebuild_binary() -> None:
    proc = subprocess.run(
        ["/opt/verifier-scripts/rebuild-tool"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr


def _clear_outputs() -> None:
    for path in (
        STAGING_PATH,
        RECONCILE_PATH,
        SNAPSHOT_PATH,
        RECORDS_PATH,
        INDEX_PATH,
        AUDIT_PATH,
    ):
        if path.exists():
            path.unlink()


def _run_cli(*extra: str) -> subprocess.CompletedProcess[str]:
    _rebuild_binary()
    _clear_outputs()
    return subprocess.run([str(BINARY), *extra], capture_output=True, text=True)


def _run_ingest_only() -> subprocess.CompletedProcess[str]:
    _rebuild_binary()
    _clear_outputs()
    return subprocess.run([str(BINARY), "ingest"], capture_output=True, text=True)


def _run_reconcile_only() -> subprocess.CompletedProcess[str]:
    _rebuild_binary()
    return subprocess.run([str(BINARY), "reconcile"], capture_output=True, text=True)


def _run_export_only() -> subprocess.CompletedProcess[str]:
    _rebuild_binary()
    for path in (RECORDS_PATH, INDEX_PATH, AUDIT_PATH):
        if path.exists():
            path.unlink()
    return subprocess.run([str(BINARY), "export"], capture_output=True, text=True)


def _run_cli_keep_state(*extra: str) -> subprocess.CompletedProcess[str]:
    """Run CLI without clearing snapshot or prior export audit (for rerun/idempotency checks)."""
    _rebuild_binary()
    return subprocess.run([str(BINARY), *extra], capture_output=True, text=True)


@pytest.fixture(scope="module", autouse=True)
def build_once():
    proc = _run_cli()
    assert proc.returncode in {0, 3}, proc.stderr
    yield


@pytest.fixture
def restore_baseline_env():
    if BASELINE_BACKUP.exists():
        shutil.rmtree(BASELINE_BACKUP)
    if POLICY_BACKUP.exists():
        POLICY_BACKUP.unlink()
    shutil.copytree(SESSIONS, BASELINE_BACKUP)
    shutil.copy2(POLICY, POLICY_BACKUP)
    yield
    shutil.rmtree(SESSIONS)
    shutil.copytree(BASELINE_BACKUP, SESSIONS)
    shutil.copy2(POLICY_BACKUP, POLICY)


class TestCoreCorrectness:
    def test_binary_exists(self):
        """neural-echo-forge must be built at /app/neural-echo-forge."""
        assert BINARY.is_file()

    def test_baseline_records_match_reference(self):
        """memory-records.json must match independent reference export."""
        _, _, expected_records, _, _ = build_outputs()
        actual_records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        assert actual_records == expected_records

    def test_baseline_index_matches_reference(self):
        """retrieval-index.json must match reference bucket ordering."""
        _, _, _, expected_index, _ = build_outputs()
        actual_index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        assert actual_index == expected_index
        assert list(actual_index["user:alice"].keys()) == list(
            expected_index["user:alice"].keys()
        )

    def test_baseline_audit_matches_reference(self):
        """memory-audit.json counters must match reference except live digests."""
        snap_bytes = SNAPSHOT_PATH.read_bytes()
        staging_bytes = STAGING_PATH.read_bytes()
        _, staging, _, _, expected_audit = build_outputs()
        actual_audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
        expected_audit["snapshot_digest_sha256"] = digest_snapshot_bytes(snap_bytes)
        expected_audit["staging_digest_sha256"] = hashlib.sha256(staging_bytes).hexdigest()
        assert actual_audit == expected_audit
        assert staging["export_mode"] == "closed"
        assert staging["conflict_mode"] == "closed"

    def test_reconcile_report_written_by_subcommand(self):
        """reconcile must write reconcile-report.json matching snapshot and staging."""
        proc = _run_ingest_only()
        assert proc.returncode in {0, 3}, proc.stderr
        rec = _run_reconcile_only()
        assert rec.returncode == 0, rec.stderr
        report = json.loads(RECONCILE_PATH.read_text(encoding="utf-8"))
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        staging = json.loads(STAGING_PATH.read_text(encoding="utf-8"))
        assert report["snapshot_seq"] == snapshot["snapshot_seq"]
        assert report["staging_seq"] == staging["staging_seq"]
        assert report["fingerprint_valid"] is True
        assert report["ingest_fingerprint"] == snapshot["ingest_fingerprint"]
        assert report["conflict_mode"] == staging["conflict_mode"]
        assert report["export_mode"] == staging["export_mode"]

    def test_export_requires_reconcile_report(self):
        """export after ingest without reconcile must exit 2."""
        _run_ingest_only()
        proc = _run_export_only()
        assert proc.returncode == 2

    def test_relative_policy_path_rejected(self, restore_baseline_env, monkeypatch):
        """relative NEF_POLICY_PATH must make ingest exit 2."""
        monkeypatch.setenv("NEF_POLICY_PATH", "data/policies/memory-policy.json")
        proc = _run_ingest_only()
        assert proc.returncode == 2

    def test_staging_ledger_written_by_ingest(self):
        """ingest must write ingest-staging.json with candidate digest before snapshot."""
        proc = _run_ingest_only()
        assert proc.returncode in {0, 3}, proc.stderr
        staging = json.loads(STAGING_PATH.read_text(encoding="utf-8"))
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        _, expected_staging = ingest_all()
        assert staging == expected_staging
        assert staging["staging_seq"] == snapshot["snapshot_seq"]
        assert staging["candidate_count"] > 0

    def test_snapshot_written_by_ingest(self):
        """ingest alone must write memory-snapshot.json with active and vault rows."""
        proc = _run_ingest_only()
        assert proc.returncode in {0, 3}, proc.stderr
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        assert snapshot["active_memories"]
        assert snapshot["retention_vault"]
        assert any(row["tier"] == "ephemeral" for row in snapshot["retention_vault"])

    def test_export_requires_snapshot(self):
        """export without snapshot must exit 2."""
        _clear_outputs()
        proc = _run_export_only()
        assert proc.returncode == 2

    def test_export_requires_staging_ledger(self):
        """export without ingest-staging.json must exit 2."""
        _run_ingest_only()
        _run_reconcile_only()
        STAGING_PATH.unlink()
        proc = _run_export_only()
        assert proc.returncode == 2

    def test_export_reads_snapshot_only(self):
        """export must not change staged vault rows or staging ledger."""
        _run_ingest_only()
        _run_reconcile_only()
        before = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        staging_before = STAGING_PATH.read_bytes()
        vault_len = len(before["retention_vault"])
        proc = _run_export_only()
        assert proc.returncode == 0, proc.stderr
        after = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        assert len(after["retention_vault"]) == vault_len
        assert STAGING_PATH.read_bytes() == staging_before

    def test_index_predicate_discovery_order(self):
        """predicate keys must follow discovery_seq order per export-artifacts.md."""
        actual_index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        _, _, _, expected_index, _ = build_outputs()
        assert list(actual_index["user:alice"].keys()) == list(
            expected_index["user:alice"].keys()
        )
        preds = list(actual_index["user:alice"].keys())
        assert preds[0] == "timezone"
        assert preds[-1] == "drink_pref"

    def test_drink_pref_winner_is_latest_temporal(self):
        """drink_pref export record must reflect highest anchor_ms winner in closed mode."""
        records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        drink = [r for r in records["records"] if r["predicate"] == "drink_pref"]
        assert len(drink) == 1
        assert drink[0]["memory_id"] == "mem-004"
        assert drink[0]["object"] == "almond milk latte"

    def test_semantic_dedup_hobby(self):
        """profile hobby and tool hobby must dedup to tool row in export."""
        records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        hobbies = [r for r in records["records"] if r["predicate"] == "hobby"]
        assert len(hobbies) == 1
        assert hobbies[0]["memory_id"] == "mem-hobby"

    def test_rerun_unchanged_inputs_byte_identical(self, restore_baseline_env):
        """unchanged second run must match prior outputs except snapshot_seq and export_generation."""
        first = _run_cli()
        assert first.returncode == 3, first.stderr
        first_snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        first_staging = json.loads(STAGING_PATH.read_text(encoding="utf-8"))
        first_records = RECORDS_PATH.read_bytes()
        first_index = INDEX_PATH.read_bytes()
        first_audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

        second = _run_cli_keep_state()
        assert second.returncode == 3, second.stderr
        second_snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        second_staging = json.loads(STAGING_PATH.read_text(encoding="utf-8"))
        second_records = RECORDS_PATH.read_bytes()
        second_index = INDEX_PATH.read_bytes()
        second_audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))

        assert second_snapshot["snapshot_seq"] == first_snapshot["snapshot_seq"] + 1
        assert second_staging["staging_seq"] == first_staging["staging_seq"] + 1
        assert second_audit["export_generation"] == first_audit["export_generation"] + 1

        first_cmp = dict(first_snapshot)
        second_cmp = dict(second_snapshot)
        first_cmp.pop("snapshot_seq")
        second_cmp.pop("snapshot_seq")
        assert second_cmp == first_cmp

        first_records_doc = json.loads(first_records)
        second_records_doc = json.loads(second_records)
        first_records_doc.pop("snapshot_seq", None)
        second_records_doc.pop("snapshot_seq", None)
        assert second_records_doc == first_records_doc
        assert second_index == first_index

        first_audit_cmp = dict(first_audit)
        second_audit_cmp = dict(second_audit)
        first_audit_cmp.pop("export_generation")
        second_audit_cmp.pop("export_generation")
        first_audit_cmp.pop("snapshot_digest_sha256", None)
        second_audit_cmp.pop("snapshot_digest_sha256", None)
        first_audit_cmp.pop("staging_digest_sha256", None)
        second_audit_cmp.pop("staging_digest_sha256", None)
        assert second_audit_cmp == first_audit_cmp


class TestAdversarialTraps:
    def test_hidden_shuffle_same_outputs(self, restore_baseline_env, monkeypatch):
        """shuffled hidden session order must yield identical export records."""
        shutil.rmtree(SESSIONS)
        shutil.copytree(HIDDEN_SESSIONS, SESSIONS)
        monkeypatch.setenv("NEF_SESSIONS_ROOT", str(SESSIONS))
        proc = _run_cli()
        assert proc.returncode in {0, 3}, proc.stderr
        _, _, expected_records, expected_index, _ = build_outputs(sessions_root=SESSIONS)
        actual_records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        actual_index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        assert actual_records == expected_records
        assert actual_index == expected_index

    def test_hidden_open_mode_confidence_winner(self, restore_baseline_env, monkeypatch):
        """open conflict_mode must pick higher confidence over later anchor_ms at ingest."""
        shutil.rmtree(SESSIONS)
        shutil.copytree(HIDDEN_SESSIONS, SESSIONS)
        shutil.copy2(HIDDEN_POLICY, POLICY)
        monkeypatch.setenv("NEF_SESSIONS_ROOT", str(SESSIONS))
        monkeypatch.setenv("NEF_POLICY_PATH", str(HIDDEN_POLICY))
        proc = _run_cli()
        assert proc.returncode in {0, 3}, proc.stderr
        records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        notify = [r for r in records["records"] if r["predicate"] == "notify_pref"]
        assert len(notify) == 1
        assert notify[0]["memory_id"] == "mem-open-a"
        assert notify[0]["object"] == "sms"
        staging = json.loads(STAGING_PATH.read_text(encoding="utf-8"))
        assert staging["conflict_mode"] == "open"
        assert staging["export_mode"] == "open"

    def test_hidden_split_conflict_closed_export_open(self, restore_baseline_env, monkeypatch):
        """closed conflict_mode must win at ingest even when export_mode is open."""
        shutil.rmtree(SESSIONS)
        shutil.copytree(HIDDEN_SESSIONS, SESSIONS)
        shutil.copy2(HIDDEN_POLICY_SPLIT, POLICY)
        monkeypatch.setenv("NEF_SESSIONS_ROOT", str(SESSIONS))
        monkeypatch.setenv("NEF_POLICY_PATH", str(HIDDEN_POLICY_SPLIT))
        proc = _run_cli()
        assert proc.returncode in {0, 3}, proc.stderr
        records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        notify = [r for r in records["records"] if r["predicate"] == "notify_pref"]
        assert len(notify) == 1
        assert notify[0]["memory_id"] == "mem-open-b"
        staging = json.loads(STAGING_PATH.read_text(encoding="utf-8"))
        assert staging["conflict_mode"] == "closed"
        assert staging["export_mode"] == "open"

    def test_mutate_then_reference_still_passes(self, restore_baseline_env):
        """echo-mutate perturbation must still match reference on rebuilt run."""
        mutate = subprocess.run(
            ["/opt/verifier-scripts/echo-mutate", "--seed", str(ADV_SEED)],
            capture_output=True,
            text=True,
        )
        assert mutate.returncode == 0, mutate.stderr
        proc = _run_cli()
        assert proc.returncode in {0, 3}, proc.stderr
        snapshot, staging = ingest_all()
        assert snapshot["reference_anchor_ms"] == json.loads(
            SNAPSHOT_PATH.read_text(encoding="utf-8")
        )["reference_anchor_ms"]
        records_doc, index, _ = export_from_snapshot(
            snapshot,
            staging,
            staging_bytes=STAGING_PATH.read_bytes(),
        )
        assert json.loads(RECORDS_PATH.read_text(encoding="utf-8")) == records_doc
        assert json.loads(INDEX_PATH.read_text(encoding="utf-8")) == index

    def test_hidden_cross_group_correction_rejected(self, restore_baseline_env, monkeypatch):
        """a correction whose target lives in another subject/predicate group must be dropped, leaving the target exported."""
        shutil.rmtree(SESSIONS)
        shutil.copytree(HIDDEN_SESSIONS, SESSIONS)
        monkeypatch.setenv("NEF_SESSIONS_ROOT", str(SESSIONS))
        proc = _run_cli()
        assert proc.returncode in {0, 3}, proc.stderr
        _, _, expected_records, _, _ = build_outputs(sessions_root=SESSIONS)
        records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        assert records == expected_records
        dave = {(r["predicate"], r["memory_id"], r["object"]) for r in records["records"] if r["subject"] == "user:dave"}
        assert ("team", "mem-d2", "platform") in dave
        assert not any(r["predicate"] == "shift" for r in records["records"] if r["subject"] == "user:dave")
        assert "nights" not in {r["object"] for r in records["records"]}

    def test_hidden_missing_correction_target_superseded(self, restore_baseline_env, monkeypatch):
        """a correction targeting an id absent from its own group must supersede itself, not win temporally."""
        shutil.rmtree(SESSIONS)
        shutil.copytree(HIDDEN_SESSIONS, SESSIONS)
        monkeypatch.setenv("NEF_SESSIONS_ROOT", str(SESSIONS))
        proc = _run_cli()
        assert proc.returncode in {0, 3}, proc.stderr
        records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        role = [r for r in records["records"] if r["subject"] == "user:dave" and r["predicate"] == "role"]
        assert len(role) == 1
        assert role[0]["memory_id"] == "mem-d1"
        assert role[0]["object"] == "engineer"
        assert "manager" not in {r["object"] for r in records["records"]}
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        superseded_ids = {r["memory_id"] for r in snapshot["superseded_memories"]}
        assert "mem-nope" in superseded_ids

    def test_hidden_transitive_correction_chain(self, restore_baseline_env, monkeypatch):
        """a chain of corrections (each becoming the next target) must resolve to the final tip, not the first hop."""
        shutil.rmtree(SESSIONS)
        shutil.copytree(HIDDEN_SESSIONS, SESSIONS)
        monkeypatch.setenv("NEF_SESSIONS_ROOT", str(SESSIONS))
        proc = _run_cli()
        assert proc.returncode in {0, 3}, proc.stderr
        _, _, expected_records, _, _ = build_outputs(sessions_root=SESSIONS)
        records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        assert records == expected_records
        role = [
            r
            for r in records["records"]
            if r["subject"] == "user:erin" and r["predicate"] == "role"
        ]
        assert len(role) == 1
        assert role[0]["memory_id"] == "mem-e3"
        assert role[0]["object"] == "lead"
        exported_objects = {r["object"] for r in records["records"]}
        assert "analyst" not in exported_objects
        assert "intern" not in exported_objects
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        superseded_ids = {r["memory_id"] for r in snapshot["superseded_memories"]}
        assert {"mem-e1", "mem-e2"} <= superseded_ids

    def test_hidden_correction_cycle_rejected(self, restore_baseline_env, monkeypatch):
        """two corrections that only target each other form a cycle; both must be dropped and the base memory kept."""
        shutil.rmtree(SESSIONS)
        shutil.copytree(HIDDEN_SESSIONS, SESSIONS)
        monkeypatch.setenv("NEF_SESSIONS_ROOT", str(SESSIONS))
        proc = _run_cli()
        assert proc.returncode in {0, 3}, proc.stderr
        records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        city = [
            r
            for r in records["records"]
            if r["subject"] == "user:erin" and r["predicate"] == "city"
        ]
        assert len(city) == 1
        assert city[0]["memory_id"] == "mem-c1"
        assert city[0]["object"] == "paris"
        exported_objects = {r["object"] for r in records["records"]}
        assert "london" not in exported_objects
        assert "tokyo" not in exported_objects
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        superseded_ids = {r["memory_id"] for r in snapshot["superseded_memories"]}
        assert {"mem-cx", "mem-cy"} <= superseded_ids

    def test_staging_vault_exceeds_export_records(self):
        """snapshot must retain vault rows omitted from exported records."""
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        assert len(snapshot["retention_vault"]) > 0
        assert len(snapshot["active_memories"]) >= len(records["records"])

    def test_superseded_not_in_export(self):
        """a superseded memory must not reappear in memory-records.json as the same memory."""
        snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        records = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
        exported = {
            (row["memory_id"], row["subject"], row["predicate"])
            for row in records["records"]
        }
        for row in snapshot["superseded_memories"]:
            assert (row["memory_id"], row["subject"], row["predicate"]) not in exported
