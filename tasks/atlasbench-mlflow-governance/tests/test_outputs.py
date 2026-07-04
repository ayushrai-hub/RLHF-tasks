"""Public smoke and invariant tests for atlas-harden (no full policy oracle)."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest
import tomllib
import yaml

from verifier_helpers import (
    HEX64,
    assert_schema_contract,
    configs_digest,
    evidence_chain_digest,
    list_participating_paths,
    read_policy_actions,
    read_run_summary,
    value_digest,
)

DOSSIER = Path("/app/data/governance-dossier.md")
CONFIG_DIR = Path("/app/data/configs")
OUT_DIR = Path("/app/output/configs")
EVIDENCE = Path("/app/output/evidence.db")
BINARY = Path("/app/bin/atlas-harden")
HARDEN_SRC = Path("/app/atlas-harden")
WORKSPACE_ID = "atlas-west"


def _run_harden(config_dir: Path, out_dir: Path, evidence: Path) -> subprocess.CompletedProcess:
    out_dir.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            str(BINARY),
            "--dossier",
            str(DOSSIER),
            "--config-dir",
            str(config_dir),
            "--out-dir",
            str(out_dir),
            "--evidence",
            str(evidence),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def _rebuild_binary() -> None:
    result = subprocess.run(
        ["go", "build", "-o", str(BINARY), "."],
        cwd=str(HARDEN_SRC),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"go build failed:\n{result.stderr}"


@pytest.fixture(scope="module", autouse=True)
def rebuild_and_harden() -> None:
    _rebuild_binary()
    result = _run_harden(CONFIG_DIR, OUT_DIR, EVIDENCE)
    assert result.returncode == 0, result.stderr


def test_evidence_database_exists_with_summary():
    assert EVIDENCE.exists()
    summary = read_run_summary(EVIDENCE)
    assert summary["action_count"] >= 1
    assert summary["profile_count"] >= 1


def test_evidence_sqlite_schema_contract():
    assert_schema_contract(EVIDENCE)
    summary = read_run_summary(EVIDENCE)
    for field in (
        "dossier_digest",
        "input_configs_digest",
        "output_configs_digest",
        "evidence_chain_digest",
    ):
        assert isinstance(summary[field], str)
        assert HEX64.match(summary[field]), f"{field} must be lowercase sha256 hex"


def test_dossier_and_config_digests_match_helpers():
    input_paths = list_participating_paths(CONFIG_DIR)
    out_paths = list_participating_paths(OUT_DIR)
    summary = read_run_summary(EVIDENCE)
    assert summary["dossier_digest"] == hashlib.sha256(DOSSIER.read_bytes()).hexdigest()
    assert summary["input_configs_digest"] == configs_digest(CONFIG_DIR, input_paths)
    assert summary["output_configs_digest"] == configs_digest(OUT_DIR, out_paths)


def test_run_summary_counts_match_tables():
    summary = read_run_summary(EVIDENCE)
    conn = sqlite3.connect(EVIDENCE)
    try:
        assert summary["action_count"] == conn.execute("SELECT COUNT(*) FROM policy_actions").fetchone()[0]
        assert summary["exception_resolution_count"] == conn.execute(
            "SELECT COUNT(*) FROM exception_resolution"
        ).fetchone()[0]
        assert summary["uri_redaction_count"] == conn.execute(
            "SELECT COUNT(*) FROM uri_redactions"
        ).fetchone()[0]
        assert summary["lineage_edge_count"] == conn.execute(
            "SELECT COUNT(*) FROM lineage_edges"
        ).fetchone()[0]
    finally:
        conn.close()


def test_evidence_chain_digest_matches_policy_actions():
    summary = read_run_summary(EVIDENCE)
    assert summary["evidence_chain_digest"] == evidence_chain_digest(EVIDENCE)


def test_policy_action_value_digests():
    for row in read_policy_actions(EVIDENCE):
        expected = value_digest(
            row["rule_id"],
            row["target_path"],
            row["old_value"],
            row["new_value"],
            row["status"],
        )
        assert row["value_digest"] == expected


def test_experiment_exception_keeps_alpha_public_read():
    data = yaml.safe_load((OUT_DIR / "experiments.yaml").read_text())
    by_id = {item["id"]: item for item in data["experiments"]}
    assert by_id["exp-alpha"]["artifacts"]["public_read"] is True
    assert by_id["exp-beta"]["artifacts"]["public_read"] is False
    assert by_id["exp-gamma"]["artifacts"]["public_read"] is False


def test_tracking_uri_and_server_use_env_credential_reference():
    data = yaml.safe_load((OUT_DIR / "tracking.yaml").read_text())
    uri = data["tracking"]["uri"]
    assert uri == "https://admin:env:ATLAS_TRACK_TOKEN@track.atlasbench.internal/mlflow"
    primary = next(s for s in data["tracking"]["servers"] if s["name"] == "primary")
    assert primary["uri"] == uri


def test_retention_inheritance_and_override():
    data = yaml.safe_load((OUT_DIR / "tracking.yaml").read_text())
    by_id = {item["id"]: item for item in data["tracking"]["experiments"]}
    assert by_id["exp-alpha"]["retention"]["class"] == "standard-90d"
    assert by_id["exp-gamma"]["retention"]["class"] == "standard-90d"
    assert by_id["exp-beta"]["retention"]["class"] == "archive-7y"


def test_registry_alias_mutability_and_skipped_conflict():
    data = tomllib.loads((OUT_DIR / "registry.toml").read_text())
    by_name = {item["name"]: item for item in data["models"]}
    assert by_name["churn-staging"]["aliases"]["mutable"] is True
    assert by_name["churn-prod"]["aliases"]["mutable"] is False
    rows = read_policy_actions(EVIDENCE)
    skipped = [
        r for r in rows if r["status"] == "skipped_conflict" and r["rule_id"] == "RM-002"
    ]
    assert any(r["exception_id"] == "EX-E-021" for r in skipped)


def test_lg005_quarantine_for_missing_and_quarantined_experiments():
    data = tomllib.loads((OUT_DIR / "registry.toml").read_text())
    by_name = {item["name"]: item for item in data["models"]}
    assert by_name["orphan-model"]["governance"]["quarantine"] is True
    assert by_name["linked-quarantine"]["governance"]["quarantine"] is True
    rows = read_policy_actions(EVIDENCE)
    orphan = [
        r
        for r in rows
        if r["rule_id"] == "LG-005" and "orphan-model" in r["target_path"]
    ]
    assert orphan and orphan[0]["status"] == "applied"
    assert orphan[0]["reason_code"] == "lineage_missing_experiment"


def test_workspace_artifact_public_read_hardened():
    data = tomllib.loads((OUT_DIR / "workspace.toml").read_text())
    assert data["artifacts"]["public_read"] is False


def test_exception_resolution_records_inactive_and_window_miss():
    conn = sqlite3.connect(EVIDENCE)
    try:
        statuses = {
            row[0]
            for row in conn.execute(
                "SELECT resolution_status FROM exception_resolution"
            ).fetchall()
        }
        assert "inactive" in statuses
        assert "window_miss" in statuses
    finally:
        conn.close()


def test_stale_output_file_removed(tmp_path):
    stale = OUT_DIR / "stale-leftover.toml"
    stale.write_text("stale=true\n")
    result = _run_harden(CONFIG_DIR, OUT_DIR, tmp_path / "evidence.db")
    assert result.returncode == 0, result.stderr
    assert not stale.exists()


def test_idempotent_second_run_produces_identical_evidence_and_outputs(tmp_path):
    first_db = EVIDENCE.read_bytes()
    first_out = {
        rel: (OUT_DIR / rel).read_bytes()
        for rel in list_participating_paths(OUT_DIR)
    }
    result = _run_harden(CONFIG_DIR, OUT_DIR, EVIDENCE)
    assert result.returncode == 0, result.stderr
    assert EVIDENCE.read_bytes() == first_db
    for rel, content in first_out.items():
        assert (OUT_DIR / rel).read_bytes() == content


def test_dynamic_mutation_changes_digest(tmp_path):
    dynamic_dir = tmp_path / "configs"
    dynamic_out = tmp_path / "out"
    dynamic_db = tmp_path / "evidence.db"
    shutil.copytree(CONFIG_DIR, dynamic_dir)
    exp_path = dynamic_dir / "experiments.yaml"
    data = yaml.safe_load(exp_path.read_text())
    data["experiments"].append({"id": "exp-dynamic", "artifacts": {"public_read": True}})
    exp_path.write_text(yaml.dump(data, sort_keys=False, default_flow_style=False))

    track_path = dynamic_dir / "tracking.yaml"
    track = yaml.safe_load(track_path.read_text())
    track["tracking"]["experiments"].append({"id": "exp-dynamic", "retention": {"override": False}})
    track_path.write_text(yaml.dump(track, sort_keys=False, default_flow_style=False))

    result = _run_harden(dynamic_dir, dynamic_out, dynamic_db)
    assert result.returncode == 0, result.stderr
    baseline = read_run_summary(EVIDENCE)
    variant = read_run_summary(dynamic_db)
    assert variant["input_configs_digest"] != baseline["input_configs_digest"]
    assert variant["action_count"] != baseline["action_count"]
