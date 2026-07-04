"""Love letter collection preservation planner verification tests."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from preservation_harness import run, run_checked
from preservation_verify_suite import (
    BIN_EXPORT,
    BIN_INGEST,
    DEFAULT_ARCHIVE,
    FRAGILE_TRAP,
    PRESERVATION_ATLAS,
    STORAGE_TRAP,
    PreservationVerifier,
    WORK_MIRROR,
)
from reference_preservation_plan import reference_preservation

V = PreservationVerifier


def test_whitmore_folio_reference_digest() -> None:
    """Independent oracle must recompute whitmore folio digest from bundled heirloom-archive."""
    ref = reference_preservation(DEFAULT_ARCHIVE)
    assert ref["pools"]["era_count"] >= 3
    assert ref["rollup"]["format_count"] >= 3


def test_intake_seals_collection_capture() -> None:
    """Intake must write validated collection-snapshot.json for bundled archive."""
    V().reset_workspace().run_full_pipeline().assert_collection_snapshot_valid()


def test_repeat_intake_stable_folio_digest() -> None:
    """Repeat intake on unchanged letterfolio must keep collection_snapshot_hash stable."""
    v = V().reset_workspace().run_full_pipeline()
    first = json.loads(Path("/app/state/collection-snapshot.json").read_text())["collection_snapshot_hash"]
    v.ingest_only(DEFAULT_ARCHIVE)
    second = json.loads(Path("/app/state/collection-snapshot.json").read_text())["collection_snapshot_hash"]
    assert first == second


def test_registry_counter_advances_on_duplicate_scan() -> None:
    """ingest-manifest run_sequence must advance when letterfolio bytes are unchanged."""
    V().reset_workspace().run_full_pipeline()
    seq1 = json.loads(Path("/app/state/ingest-manifest.json").read_text())["run_sequence"]
    run_checked([str(BIN_INGEST)])
    seq2 = json.loads(Path("/app/state/ingest-manifest.json").read_text())["run_sequence"]
    assert seq2 == seq1 + 1


def test_era_clustering_rejects_keepsake_bins() -> None:
    """redundancy-pools must cluster artifacts by ERA tag not keepsake box."""
    V().reset_workspace().run_full_pipeline().assert_era_pools_match_reference()
    assert Path("/app/state/redundancy-pools.json").is_file()


def test_format_transcoding_rollup_materializes() -> None:
    """Intake must materialize migration-rollup.json with format transcoding groups."""
    V().reset_workspace().run_full_pipeline()
    rollup = json.loads(Path("/app/state/migration-rollup.json").read_text())
    assert rollup["schema_version"] == 1
    assert rollup["format_groups"]


def test_conservator_summary_after_publish() -> None:
    """Publish must materialize preservation-report.json conservator summary."""
    V().reset_workspace().run_full_pipeline()
    assert Path("/app/output/preservation-report.json").is_file()


def test_format_transcoding_not_keepsake_sort() -> None:
    """migration-rollup must group artifacts by FORMAT tag not keepsake box."""
    V().reset_workspace().run_full_pipeline().assert_migration_rollup_match_reference()


def test_crossref_witness_dedupes_edges() -> None:
    """index-ledger index_edges must be sorted unique cross-reference witness pairs."""
    V().reset_workspace().run_full_pipeline().assert_index_ledger_match_reference()
    ledger = json.loads(Path("/app/state/index-ledger.json").read_text())
    assert ledger["schema_version"] == 1


def test_chronology_queue_priority_seeding() -> None:
    """preservation-staging priority_queue must follow priority score not plain id sort."""
    V().reset_workspace().run_full_pipeline().assert_preservation_staging_match_reference()


def test_mirror_pairing_round_one_transcode() -> None:
    """Round-one migrations must pair queue[i] with queue[n-1-i] per preservation-staging.md."""
    v = V().reset_workspace().run_full_pipeline()
    staging = json.loads(Path("/app/state/preservation-staging.json").read_text())
    ref = v.reference()
    assert staging["migration_pairs"] == ref["staging"]["migration_pairs"]
    assert len(staging["migration_pairs"]) == 4


def test_vault_wave_bands_compress_slots() -> None:
    """preservation_waves must group migrations by media slot band not one wave per pair."""
    V().reset_workspace().run_full_pipeline()
    staging = json.loads(Path("/app/state/preservation-staging.json").read_text())
    assert len(staging["preservation_waves"]) < len(staging["migration_pairs"])


def test_byte_cap_envelope_honored_in_staging() -> None:
    """preservation-staging within_storage_budget must be true when byte cap envelope is honored."""
    v = V().reset_workspace().run_full_pipeline()
    staging = json.loads(Path("/app/state/preservation-staging.json").read_text())
    assert staging["within_storage_budget"] is True
    assert staging["within_storage_budget"] == v.reference()["staging"]["within_storage_budget"]


def test_registry_witness_binds_all_captures() -> None:
    """ingest-manifest must witness-bind snapshot redundancy rollup index and schedule digests."""
    V().reset_workspace().run_full_pipeline().assert_manifest_binds_all_layers()


def test_publish_emits_atlas_and_conservator_report() -> None:
    """Publish must write preservation-atlas.json and preservation-report.json."""
    V().reset_workspace().run_full_pipeline().assert_atlas_and_preservation_report()


def test_idempotent_publish_atlas_bytes() -> None:
    """Re-publish on unchanged staging must yield byte-identical preservation atlas."""
    v = V().reset_workspace().run_full_pipeline()
    first = PRESERVATION_ATLAS.read_bytes()
    v.export_only()
    assert PRESERVATION_ATLAS.read_bytes() == first


def test_heirloom_root_override_hidden_vault() -> None:
    """HEIRLOOM_ARCHIVE_ROOT must override default heirloom-archive root."""
    v = V().with_archive_root(STORAGE_TRAP, env={"HEIRLOOM_ARCHIVE_ROOT": str(STORAGE_TRAP)})
    v.reset_workspace().run_full_pipeline()
    snap = json.loads(Path("/app/state/collection-snapshot.json").read_text())
    ids = {e["artifact_id"] for e in snap["artifacts"]}
    assert "art-t01" in ids
    assert Path("/opt/verifier-fixtures/storage_policy_trap/collection.json").is_file()


def test_quarantine_storage_trap_wave_split() -> None:
    """Hidden quarantine storage_policy_trap requires correct vault wave grouping."""
    v = V().with_archive_root(STORAGE_TRAP, env={"HEIRLOOM_ARCHIVE_ROOT": str(STORAGE_TRAP)})
    v.reset_workspace().run_full_pipeline().assert_preservation_staging_match_reference()
    assert Path("/opt/verifier-fixtures/storage_policy_trap/collection.json").is_file()


def test_fragile_acid_free_pairing_avoids_trap() -> None:
    """Hidden fragile_trap must avoid FRAGILE pairs in round-one transcode plan."""
    v = V().with_archive_root(FRAGILE_TRAP, env={"HEIRLOOM_ARCHIVE_ROOT": str(FRAGILE_TRAP)})
    v.reset_workspace().run_full_pipeline()
    staging = json.loads(Path("/app/state/preservation-staging.json").read_text())
    for p in staging["migration_pairs"]:
        assert p["primary"] != p["replica"]
    assert Path("/opt/verifier-fixtures/fragile_trap/collection.json").is_file()


def test_publish_aborts_on_missing_captures() -> None:
    """Publish must abort when staging capture artifacts are missing."""
    V().reset_workspace()
    proc = run([str(BIN_EXPORT)])
    assert proc.returncode != 0


def test_staging_checksum_matches_oracle_witness() -> None:
    """preservation-staging schedule_hash must match independent oracle witness."""
    v = V().reset_workspace().run_full_pipeline()
    staging = json.loads(Path("/app/state/preservation-staging.json").read_text())
    assert staging["schedule_hash"] == v.reference()["staging"]["schedule_hash"]


def test_chronology_offsets_preserve_negative_slots() -> None:
    """parse_letterfolio must preserve negative MEDIA_SLOT chronology offsets."""
    V().reset_workspace().run_full_pipeline().assert_negative_media_slots_preserved()


def test_conservator_wave_tally_matches_atlas() -> None:
    """preservation-report wave_count must equal preservation_waves length in atlas."""
    V().reset_workspace().run_full_pipeline()
    report = json.loads(Path("/app/output/preservation-report.json").read_text())
    atlas = json.loads(Path("/app/output/preservation-atlas.json").read_text())
    assert report["wave_count"] == len(atlas["preservation_waves"])


def test_vault_mirror_path_matches_oracle() -> None:
    """Pipeline on copied archive root under work dir must match oracle transcode plan."""
    WORK_MIRROR.mkdir(parents=True, exist_ok=True)
    dest = WORK_MIRROR / "mirror-heirloom-archive"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(DEFAULT_ARCHIVE, dest)
    v = V().with_archive_root(dest)
    v.reset_workspace().run_full_pipeline()
    ref = v.reference()
    atlas = json.loads(PRESERVATION_ATLAS.read_text())
    assert atlas["migration_pairs"] == ref["atlas"]["migration_pairs"]


def test_default_heirloom_letterfolio_layout() -> None:
    """Bundled intake must read letterfolio fragments from /app/heirloom-archive/letterfolio."""
    assert (DEFAULT_ARCHIVE / "letterfolio").is_dir()
    V().reset_workspace().run_full_pipeline()
    snap = json.loads(Path("/app/state/collection-snapshot.json").read_text())
    assert snap["collection"]["collection_label"] == "whitmore-letters-2026"


def test_six_capture_ledgers_on_intake() -> None:
    """Intake must write every /app/state capture ledger cited in instruction."""
    V().reset_workspace().run_full_pipeline().assert_six_state_ledgers()


def test_instruction_contract_paths_materialize() -> None:
    """Every output path cited in instruction must exist after intake and publish."""
    V().reset_workspace().run_full_pipeline().assert_instruction_paths_exist()


def test_staging_carries_transcode_pairs() -> None:
    """Intake must materialize preservation-staging.json with migration_pairs."""
    V().reset_workspace().run_full_pipeline()
    staging = json.loads(Path("/app/state/preservation-staging.json").read_text())
    assert staging["schema_version"] == 1
    assert staging["migration_pairs"]


def test_conservator_report_carries_witness_fingerprint() -> None:
    """Publish must materialize preservation-report.json with witness fingerprint."""
    V().reset_workspace().run_full_pipeline()
    report = json.loads(Path("/app/output/preservation-report.json").read_text())
    assert report["schema_version"] == 1
    assert "report_fingerprint" in report


def test_atlas_carries_whitmore_collection_title() -> None:
    """Publish must materialize preservation-atlas.json with collection title."""
    V().reset_workspace().run_full_pipeline()
    atlas = json.loads(Path("/app/output/preservation-atlas.json").read_text())
    assert atlas["collection_label"] == "whitmore-letters-2026"


def test_registry_carries_manifest_witness_hash() -> None:
    """Intake must materialize ingest-manifest.json with manifest witness hash."""
    V().reset_workspace().run_full_pipeline()
    manifest = json.loads(Path("/app/state/ingest-manifest.json").read_text())
    assert manifest["manifest_hash"]


def test_publish_rejects_tampered_witness_hash() -> None:
    """Publish must reject when ingest-manifest schedule_hash witness is tampered."""
    V().reset_workspace().run_full_pipeline()
    manifest = json.loads(Path("/app/state/ingest-manifest.json").read_text())
    manifest["schedule_hash"] = "0" * 64
    Path("/app/state/ingest-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    proc = run([str(BIN_EXPORT)])
    assert proc.returncode != 0
