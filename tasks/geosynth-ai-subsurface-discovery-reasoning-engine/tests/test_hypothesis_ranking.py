"""GeoSynth hypothesis ranking and discovery report verifier tests."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import (
    APP,
    FORMATION_POLICY,
    PIPELINE,
    reference_chain_fingerprint,
    reference_compose_plan,
    reference_confidence_margins,
    reference_depth_epochs,
    reference_load_traces,
    reference_margin_table_digest,
)

GUARD_LEDGER = APP / "state" / "hypothesis-guard-ledger.json"
CONFIDENCE_TABLE = APP / "state" / "confidence-margin-ledger.json"
COMPOSE_STAGING = APP / "state" / "formation-compose-staging.json"
DISCOVERY_REPORT = APP / "output" / "geosynth-discovery-report.json"
EXPORT_BIND = APP / "state" / "discovery-export-bind.json"
DISCOVERY_OK = APP / "state" / "discovery-atlas.ok"
DEPTH_EPOCHS = APP / "state" / "depth-epoch-ledger.json"


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    merged["PYTHONPATH"] = "/app"
    return subprocess.run(cmd, capture_output=True, text=True, env=merged, cwd=str(APP))


def _drive_pipeline() -> None:
    for stage in PIPELINE:
        proc = _run(["/app/bin/geosynth", stage])
        assert proc.returncode == 0, f"{stage}: {proc.stderr}{proc.stdout}"


def test_gs_guard_blocks_copper_shale_exactly():
    """guard-hypotheses records the bundled copper-belt-north versus shale-margin-east guard block."""
    for stage in ("load-surveys", "depth-epoch", "fuse-voxels", "guard-hypotheses"):
        _run(["/app/bin/geosynth", stage])
    ledger = json.loads(GUARD_LEDGER.read_text())
    assert ledger["blocked_count"] == 1
    blocked = ledger["blocked_pairs"]
    assert len(blocked) == 1
    row = blocked[0]
    policy = json.loads(FORMATION_POLICY.read_text())
    guard = policy["block_guard_pairs"][0]
    assert {row["left"], row["right"]} == {guard["left"], guard["right"]}
    assert row["reason"] == guard["reason"]


def test_gs_guard_accepts_unguarded_block_pairs():
    """guard-hypotheses accepts basalt-shale and basalt-copper pairs not listed in block_guard_pairs."""
    for stage in ("load-surveys", "depth-epoch", "fuse-voxels", "guard-hypotheses"):
        _run(["/app/bin/geosynth", stage])
    ledger = json.loads(GUARD_LEDGER.read_text())
    accepted = {(p["left"], p["right"]) for p in ledger["accepted_pairs"]}
    assert ("basalt-deep-west", "shale-margin-east") in accepted
    assert ("basalt-deep-west", "copper-belt-north") in accepted
    assert ledger["blocked_count"] == 1


def test_gs_confidence_floor_applied():
    """score-confidence applies confidence_margin = max(1 - mean prospect, confidence_floor)."""
    policy = json.loads(FORMATION_POLICY.read_text())
    floor = float(policy["confidence_floor"])
    traces = reference_load_traces()
    epochs = reference_depth_epochs(traces)
    want = reference_confidence_margins(traces, epochs, floor)
    for stage in (
        "load-surveys",
        "depth-epoch",
        "fuse-voxels",
        "guard-hypotheses",
        "score-confidence",
    ):
        _run(["/app/bin/geosynth", stage])
    table = json.loads(CONFIDENCE_TABLE.read_text())
    got = {row["block_id"]: row["confidence_margin"] for row in table["margins"]}
    for row in want:
        assert abs(got[row["block_id"]] - row["confidence_margin"]) < 1e-6
        assert got[row["block_id"]] >= floor
    assert table["margin_table_digest"] == reference_margin_table_digest(want)


def test_gs_confidence_table_lists_three_blocks():
    """score-confidence writes confidence-margin-ledger.json with margins for three blocks."""
    for stage in (
        "load-surveys",
        "depth-epoch",
        "fuse-voxels",
        "guard-hypotheses",
        "score-confidence",
    ):
        _run(["/app/bin/geosynth", stage])
    table = json.loads(CONFIDENCE_TABLE.read_text())
    assert len(table["margins"]) == 3


def test_gs_compose_branch_starts_with_pathfinder_on_tr_gc_001():
    """First copper-belt-north compose step maps tr-gc-001 to pathfinder-spike evidence_kind."""
    _drive_pipeline()
    staging = json.loads(COMPOSE_STAGING.read_text())
    copper = next(b for b in staging["compose"] if b["block_id"] == "copper-belt-north")
    assert copper["steps"][0]["sample_id"] == "tr-gc-001"
    assert copper["steps"][0]["evidence_kind"] == "pathfinder-spike"


def test_gs_compose_digest_matches_kit_reference():
    """formation_compose_digest matches lithosphere kit reference math."""
    traces = reference_load_traces()
    ref = reference_compose_plan(traces, reference_depth_epochs(traces))
    _drive_pipeline()
    staging = json.loads(COMPOSE_STAGING.read_text())
    assert staging["formation_compose_digest"] == ref["formation_compose_digest"]


def test_gs_discovery_report_chain_fingerprint():
    """geosynth-discovery-report.json discovery_fingerprint derives from chain| compose lines only."""
    traces = reference_load_traces()
    ref = reference_compose_plan(traces, reference_depth_epochs(traces))
    _drive_pipeline()
    report = json.loads(DISCOVERY_REPORT.read_text())
    assert report["discovery_store"] == "geosynth-bundled"
    want = reference_chain_fingerprint(ref["compose"])
    assert report["discovery_fingerprint"] == want
    assert len(report["discovery_fingerprint"]) == 64


def test_gs_validate_discovery_accepts_report():
    """validate-discovery exits zero on a fully synthesized discovery report."""
    _drive_pipeline()
    proc = _run(["/app/bin/geosynth", "validate-discovery"])
    assert proc.returncode == 0, proc.stderr


def test_gs_discovery_bind_finalized_epoch_three():
    """discovery-seal records discovery-export-bind.json with consolidation_epoch 3."""
    _drive_pipeline()
    bind = json.loads(EXPORT_BIND.read_text())
    assert bind["status"] == "finalized"
    assert bind["consolidation_epoch"] == 3


def test_gs_finalize_script_writes_discovery_ok():
    """finalize-discovery-atlas.sh writes discovery-atlas.ok when digests align."""
    _drive_pipeline()
    if DISCOVERY_OK.exists():
        DISCOVERY_OK.unlink()
    proc = _run(["bash", "/app/scripts/finalize-discovery-atlas.sh"])
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert DISCOVERY_OK.read_text().strip() == "ok"


def test_gs_chain_fingerprint_differs_from_epoch_fingerprint():
    """discovery_fingerprint must not equal depth-epoch epoch_digest."""
    _drive_pipeline()
    report = json.loads(DISCOVERY_REPORT.read_text())
    epochs = json.loads(DEPTH_EPOCHS.read_text())
    assert report["discovery_fingerprint"] != epochs["epoch_digest"]


def test_gs_verifier_swap_formation_policy_guards_copper_basalt():
    """Hidden verifier fixture blocks copper-belt-north versus basalt-deep-west."""
    hidden = Path("/opt/verifier-fixtures") / "hidden-formation-governance.json"
    if not hidden.is_file():
        pytest.skip("hidden fixture missing")
    backup = FORMATION_POLICY.read_text()
    try:
        shutil.copy(hidden, FORMATION_POLICY)
        for stage in ("load-surveys", "depth-epoch", "fuse-voxels", "guard-hypotheses"):
            _run(["/app/bin/geosynth", stage])
        ledger = json.loads(GUARD_LEDGER.read_text())
        blocked = {(b["left"], b["right"]) for b in ledger["blocked_pairs"]}
        assert ("copper-belt-north", "basalt-deep-west") in blocked or (
            "basalt-deep-west",
            "copper-belt-north",
        ) in blocked
    finally:
        FORMATION_POLICY.write_text(backup)


def test_gs_verifier_swap_compose_priority_puts_shale_first():
    """Hidden verifier fixture ranks shale-margin-east ahead of copper-belt-north."""
    hidden = Path("/opt/verifier-fixtures") / "hidden-hypothesis-priority.json"
    if not hidden.is_file():
        pytest.skip("hidden fixture missing")
    backup = FORMATION_POLICY.read_text()
    try:
        shutil.copy(hidden, FORMATION_POLICY)
        _drive_pipeline()
        staging = json.loads(COMPOSE_STAGING.read_text())
        assert staging["compose"][0]["block_id"] == "shale-margin-east"
    finally:
        FORMATION_POLICY.write_text(backup)
