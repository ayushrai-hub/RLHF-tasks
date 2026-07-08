"""GeoSynth survey ingest verifier tests."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from conftest import (
    APP,
    REF_LANE_TABLE,
    reference_depth_epochs,
    reference_epoch_fingerprint,
    reference_feed_fingerprint,
    reference_load_traces,
    reference_seq_book,
    reference_voxel_edges,
    reference_voxel_fingerprint,
)

SURVEY_CATALOG = APP / "state" / "survey-ingest-catalog.json"
SURVEY_SEQ = APP / "state" / "survey-seq-ledger.json"
DEPTH_EPOCHS = APP / "state" / "depth-epoch-ledger.json"
VOXEL_STAGING = APP / "state" / "voxel-staging-snapshot.json"
VOXEL_GRAPH = APP / "state" / "voxel-fusion-graph.json"
DECOY_FORMATION = APP / "data" / "decoy" / "decoy-static-formation.json"

COPPER_BELT_CHAIN = (
    "tr-gc-001",
    "tr-sq-001",
    "tr-sq-002",
    "tr-bh-001",
    "tr-gv-001",
)


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    merged["PYTHONPATH"] = "/app"
    return subprocess.run(cmd, capture_output=True, text=True, env=merged, cwd=str(APP))


def test_gs_survey_lanes_present_on_disk():
    """All six survey lanes from survey-ingest-contract.md exist on disk."""
    for lane, fname in REF_LANE_TABLE:
        assert (APP / "data" / lane / fname).is_file()


def test_gs_instruction_data_paths_exist():
    """Instruction-cited survey lanes, policies, decoy, state artifacts, and output paths exist."""
    paths = (
        "/app/data/surveys/seismic/traces.jsonl",
        "/app/data/surveys/gravity/anomalies.jsonl",
        "/app/data/surveys/magnetic/field.jsonl",
        "/app/data/surveys/borehole/logs.jsonl",
        "/app/data/surveys/geochem/samples.jsonl",
        "/app/data/surveys/hyperspectral/tiles.jsonl",
        "/app/data/decoy",
        "/app/data/decoy/decoy-static-formation.json",
        "/app/data/policies/modality-weights.json",
        "/app/data/policies/formation-governance.json",
        "/app/data/policies/formation-governance.json.bundled",
        "/app/output/geosynth-discovery-report.json",
        "/app/state/survey-ingest-catalog.json",
        "/app/state/survey-seq-ledger.json",
        "/app/state/depth-epoch-ledger.json",
        "/app/state/voxel-staging-snapshot.json",
        "/app/state/voxel-fusion-graph.json",
        "/app/state/hypothesis-guard-ledger.json",
        "/app/state/confidence-margin-ledger.json",
        "/app/state/formation-compose-staging.json",
        "/app/state/discovery-export-bind.json",
        "/app/blocks/copper-belt-north.profile.json",
    )
    for stage in ("load-surveys", "depth-epoch", "fuse-voxels", "guard-hypotheses", "score-confidence"):
        _run(["/app/bin/geosynth", stage])
    _run(["/app/bin/geosynth", "branch-formations"])
    _run(["/app/bin/geosynth", "export-discovery"])
    _run(["/app/bin/geosynth", "discovery-seal"])
    _run(["bash", "/app/scripts/finalize-discovery-atlas.sh"])
    paths = paths + ("/app/state/discovery-atlas.ok",)
    for path_str in paths:
        p = Path(path_str)
        if path_str == "/app/data/decoy":
            assert p.is_dir(), path_str
        else:
            assert p.exists(), path_str


def test_gs_decoy_formation_never_merges_exploration_blocks():
    """load-surveys must ignore decoy-static-formation.json while keeping live exploration blocks."""
    assert DECOY_FORMATION.is_file()
    _run(["/app/bin/geosynth", "load-surveys"])
    catalog = json.loads(SURVEY_CATALOG.read_text())
    blocks = {row["block_id"] for row in catalog["traces"]}
    assert {"copper-belt-north", "shale-margin-east"}.issubset(blocks)


def test_gs_catalog_sorted_by_sample_id():
    """survey-ingest-catalog.json lists traces sorted by sample_id ascending."""
    _run(["/app/bin/geosynth", "load-surveys"])
    catalog = json.loads(SURVEY_CATALOG.read_text())
    got = [r["sample_id"] for r in catalog["traces"]]
    want = [r["sample_id"] for r in reference_load_traces()]
    assert got == want


def test_gs_catalog_sha256_canonical_fingerprint():
    """catalog_digest uses geo| canonical lines with sha256 per survey-ingest-contract.md."""
    _run(["/app/bin/geosynth", "load-surveys"])
    catalog = json.loads(SURVEY_CATALOG.read_text())
    traces = reference_load_traces()
    assert catalog["catalog_digest"] == reference_feed_fingerprint(traces)


def test_gs_seq_ledger_digest_matches_grouping():
    """survey-seq-ledger.json digest matches seqbook| lines grouped by block_id."""
    _run(["/app/bin/geosynth", "load-surveys"])
    ledger = json.loads(SURVEY_SEQ.read_text())
    assert ledger["survey_seq_ledger_digest"] == reference_seq_book(reference_load_traces())


def test_gs_depth_epochs_split_three_blocks():
    """depth-epoch yields three depth epochs for bundled copper, shale, and basalt blocks."""
    _run(["/app/bin/geosynth", "load-surveys"])
    _run(["/app/bin/geosynth", "depth-epoch"])
    doc = json.loads(DEPTH_EPOCHS.read_text())
    assert len(doc["epochs"]) == 3


def test_gs_copper_belt_epoch_preserves_temporal_chain():
    """copper-belt-north epoch lists tr-gc-001 through tr-gv-001 in encounter order."""
    _run(["/app/bin/geosynth", "load-surveys"])
    _run(["/app/bin/geosynth", "depth-epoch"])
    epochs = json.loads(DEPTH_EPOCHS.read_text())["epochs"]
    copper = next(e for e in epochs if e["block_id"] == "copper-belt-north")
    assert copper["sample_ids"] == list(COPPER_BELT_CHAIN)


def test_gs_depth_epoch_fingerprint_matches_independent():
    """epoch_digest is sha256 over epoch| lines from independent segmentation."""
    traces = reference_load_traces()
    ref_epochs = reference_depth_epochs(traces)
    _run(["/app/bin/geosynth", "load-surveys"])
    _run(["/app/bin/geosynth", "depth-epoch"])
    doc = json.loads(DEPTH_EPOCHS.read_text())
    assert doc["epoch_digest"] == reference_epoch_fingerprint(ref_epochs)


def test_gs_voxel_staging_materialized_on_fuse():
    """fuse-voxels writes voxel-staging-snapshot.json before voxel-fusion-graph.json."""
    for stage in ("load-surveys", "depth-epoch", "fuse-voxels"):
        _run(["/app/bin/geosynth", stage])
    snap = json.loads(VOXEL_STAGING.read_text())
    assert snap["staging_digest"]
    assert VOXEL_GRAPH.is_file()


def test_gs_voxel_graph_includes_non_adjacent_forward_pair():
    """voxel graph links tr-gc-001 to tr-bh-001 with forward_span > 1 and borehole weight 0.68."""
    for stage in ("load-surveys", "depth-epoch", "fuse-voxels"):
        _run(["/app/bin/geosynth", stage])
    graph = json.loads(VOXEL_GRAPH.read_text())
    edge = next(e for e in graph["edges"] if e["from"] == "tr-gc-001" and e["to"] == "tr-bh-001")
    assert edge["forward_span"] > 1
    assert edge["weight"] == 0.68


def test_gs_voxel_graph_fingerprint_matches_independent():
    """voxel_graph_digest matches independent forward-pair enumeration using modality-weights.json."""
    traces = reference_load_traces()
    ref_edges = reference_voxel_edges(traces)
    for stage in ("load-surveys", "depth-epoch", "fuse-voxels"):
        _run(["/app/bin/geosynth", stage])
    graph = json.loads(VOXEL_GRAPH.read_text())
    assert graph["voxel_graph_digest"] == reference_voxel_fingerprint(ref_edges)
