"""Hidden verifier tests using fixture-specific invariants (no public policy oracle)."""

from __future__ import annotations

import shutil
import sqlite3
import subprocess
from pathlib import Path

import pytest
import tomllib
import yaml

from verifier_helpers import (
    evidence_chain_digest,
    read_policy_actions,
    read_run_summary,
)

DOSSIER = Path("/app/data/governance-dossier.md")
BINARY = Path("/app/bin/atlas-harden")
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _run(config_dir: Path, out_dir: Path, evidence: Path) -> subprocess.CompletedProcess:
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


@pytest.fixture(scope="module")
def binary_built() -> None:
    result = subprocess.run(
        ["go", "build", "-o", str(BINARY), "."],
        cwd="/app/atlas-harden",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.usefixtures("binary_built")
def test_profile_overlay_policy_pack_predicate_miss(tmp_path: Path):
    src = FIXTURES / "profile_overlay"
    config_dir = tmp_path / "cfg"
    out_dir = tmp_path / "out"
    db = tmp_path / "evidence.db"
    shutil.copytree(src, config_dir)
    result = _run(config_dir, out_dir, db)
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(db)
    try:
        pred_miss = conn.execute(
            "SELECT COUNT(*) FROM exception_resolution WHERE resolution_status='predicate_miss'"
        ).fetchone()[0]
        assert pred_miss >= 1
        disabled = conn.execute(
            "SELECT COUNT(*) FROM exception_resolution WHERE exception_id='PK-B-001'"
        ).fetchone()[0]
        assert disabled == 0
    finally:
        conn.close()

    reg = tomllib.loads((out_dir / "registry.toml").read_text())
    model = next(m for m in reg["models"] if m["name"] == "overlay-model")
    assert model["aliases"]["mutable"] is False


@pytest.mark.usefixtures("binary_built")
def test_uri_matrix_redaction_variants(tmp_path: Path):
    src = FIXTURES / "uri_matrix"
    config_dir = tmp_path / "cfg"
    out_dir = tmp_path / "out"
    db = tmp_path / "evidence.db"
    shutil.copytree(src, config_dir)
    result = _run(config_dir, out_dir, db)
    assert result.returncode == 0, result.stderr

    data = yaml.safe_load((out_dir / "tracking.yaml").read_text())
    servers = {s["name"]: s["uri"] for s in data["tracking"]["servers"]}
    assert "env:ATLAS_TRACK_TOKEN" in data["tracking"]["uri"]
    assert "env:IPV6_TRACK_TOKEN" in servers["ipv6"]
    assert servers["env-ready"] == "https://admin:env:EXISTING@track.atlasbench.internal/mlflow"
    assert servers["no-pass"] == "https://track.atlasbench.internal/mlflow"
    assert servers["ftp-bad"].startswith("ftp://")
    assert servers["unmapped"] == "https://unknown:secret@other.example.com/v1"

    conn = sqlite3.connect(db)
    try:
        statuses = {
            row[0] for row in conn.execute("SELECT status FROM uri_redactions").fetchall()
        }
        assert "redacted" in statuses
        assert "already_env" in statuses
        assert "no_password" in statuses
        assert "unsupported_scheme" in statuses
        assert "unmapped_credential" in statuses
    finally:
        conn.close()


@pytest.mark.usefixtures("binary_built")
def test_lineage_retention_quarantine_and_escaped_ids(tmp_path: Path):
    src = FIXTURES / "lineage_retention"
    config_dir = tmp_path / "cfg"
    out_dir = tmp_path / "out"
    db = tmp_path / "evidence.db"
    shutil.copytree(src, config_dir)
    result = _run(config_dir, out_dir, db)
    assert result.returncode == 0, result.stderr

    reg = tomllib.loads((out_dir / "registry.toml").read_text())
    by_name = {m["name"]: m for m in reg["models"]}
    assert by_name["model|one"]["governance"]["quarantine"] is True
    assert by_name["quarantine-link"]["governance"]["quarantine"] is True

    track = yaml.safe_load((out_dir / "tracking.yaml").read_text())
    by_id = {e["id"]: e for e in track["tracking"]["experiments"]}
    assert by_id["exp-good"]["retention"]["class"] == "extended-365d"
    assert by_id["exp-new"]["retention"]["class"] == "standard-90d"

    rows = read_policy_actions(db)
    weird_targets = [r for r in rows if "exp\\|weird" in r["target_path"] or "model\\|one" in r["target_path"]]
    assert weird_targets

    summary = read_run_summary(db)
    assert summary["evidence_chain_digest"] == evidence_chain_digest(db)


@pytest.mark.usefixtures("binary_built")
def test_verifier_fixture_replay_is_deterministic(tmp_path: Path):
    src = FIXTURES / "uri_matrix"
    config_dir = tmp_path / "cfg"
    out_dir = tmp_path / "out"
    db = tmp_path / "evidence.db"
    shutil.copytree(src, config_dir)
    assert _run(config_dir, out_dir, db).returncode == 0
    first = db.read_bytes()
    assert _run(config_dir, out_dir, db).returncode == 0
    assert db.read_bytes() == first
