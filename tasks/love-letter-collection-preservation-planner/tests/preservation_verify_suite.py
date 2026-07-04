"""Love letter preservation verification helpers."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from preservation_harness import run_checked
from reference_preservation_plan import reference_preservation

APP = Path("/app")
BIN_INGEST = APP / "heirloom-preservation" / "bin" / "heirloom-collection-intake"
BIN_EXPORT = APP / "heirloom-preservation" / "bin" / "heirloom-preservation-publish"
STATE = APP / "state"
OUTPUT = APP / "output"
COLLECTION_SNAPSHOT = STATE / "collection-snapshot.json"
REDUNDANCY_POOLS = STATE / "redundancy-pools.json"
MIGRATION_ROLLUP = STATE / "migration-rollup.json"
INDEX_LEDGER = STATE / "index-ledger.json"
PRESERVATION_STAGING = STATE / "preservation-staging.json"
INGEST_MANIFEST = STATE / "ingest-manifest.json"
PRESERVATION_ATLAS = OUTPUT / "preservation-atlas.json"
PRESERVATION_REPORT = OUTPUT / "preservation-report.json"
DEFAULT_ARCHIVE = APP / "heirloom-archive"
HIDDEN_ROOT = Path("/opt/verifier-fixtures")
STORAGE_TRAP = HIDDEN_ROOT / "storage_policy_trap"
FRAGILE_TRAP = HIDDEN_ROOT / "fragile_trap"
WORK_MIRROR = APP / "work"

INSTRUCTION_PATHS = (
    "/app/output/preservation-atlas.json",
    "/app/output/preservation-report.json",
    "/app/state/preservation-staging.json",
    "/app/state/ingest-manifest.json",
    "/app/state/collection-snapshot.json",
    "/app/state/redundancy-pools.json",
    "/app/state/migration-rollup.json",
    "/app/state/index-ledger.json",
)


class PreservationVerifier:
    """Runs heirloom-collection-intake and heirloom-preservation-publish with fluent assertions."""

    def __init__(self) -> None:
        self.archive: Path = DEFAULT_ARCHIVE
        self.env: dict[str, str] = {}

    def reset_workspace(self) -> PreservationVerifier:
        for p in (STATE, OUTPUT):
            if p.is_dir():
                shutil.rmtree(p)
        STATE.mkdir(parents=True, exist_ok=True)
        OUTPUT.mkdir(parents=True, exist_ok=True)
        return self

    def with_archive_root(self, root: Path, *, env: dict[str, str] | None = None) -> PreservationVerifier:
        self.archive = root
        self.env = dict(env or {})
        return self

    def run_full_pipeline(self) -> PreservationVerifier:
        if self.archive != DEFAULT_ARCHIVE:
            run_checked([str(BIN_INGEST), str(self.archive)], env=self.env or None)
        else:
            run_checked([str(BIN_INGEST)], env=self.env or None)
        run_checked([str(BIN_EXPORT)], env=self.env or None)
        return self

    def reference(self) -> dict:
        return reference_preservation(self.archive)

    def ingest_only(self, root: Path | None = None) -> PreservationVerifier:
        self.reset_workspace()
        target = root or self.archive
        if target == DEFAULT_ARCHIVE:
            run_checked([str(BIN_INGEST)], env=self.env or None)
        else:
            run_checked([str(BIN_INGEST), str(target)], env=self.env or None)
        return self

    def export_only(self) -> PreservationVerifier:
        run_checked([str(BIN_EXPORT)], env=self.env or None)
        return self

    def assert_collection_snapshot_valid(self) -> PreservationVerifier:
        snap = json.loads(COLLECTION_SNAPSHOT.read_text())
        assert snap["schema_version"] == 1
        assert snap["validated"] is True
        assert len(snap["artifacts"]) == 8
        return self

    def assert_era_pools_match_reference(self) -> PreservationVerifier:
        ref = self.reference()
        pools = json.loads(REDUNDANCY_POOLS.read_text())
        assert pools["eras"] == ref["pools"]["eras"]
        assert "mid-century" in pools["eras"]
        assert pools["era_count"] == ref["pools"]["era_count"]
        return self

    def assert_migration_rollup_match_reference(self) -> PreservationVerifier:
        ref = self.reference()
        rollup = json.loads(MIGRATION_ROLLUP.read_text())
        assert rollup["format_groups"] == ref["rollup"]["format_groups"]
        assert rollup["format_count"] == ref["rollup"]["format_count"]
        assert rollup["rollup_hash"] == ref["rollup"]["rollup_hash"]
        return self

    def assert_index_ledger_match_reference(self) -> PreservationVerifier:
        ref = self.reference()
        ledger = json.loads(INDEX_LEDGER.read_text())
        assert ledger["index_edges"] == ref["ledger"]["index_edges"]
        assert ledger["index_digest"] == ref["ledger"]["index_digest"]
        return self

    def assert_preservation_staging_match_reference(self) -> PreservationVerifier:
        ref = self.reference()
        staging = json.loads(PRESERVATION_STAGING.read_text())
        assert staging["priority_queue"] == ref["staging"]["priority_queue"]
        assert staging["priority_queue"] != sorted(staging["priority_queue"])
        assert staging["migration_pairs"] == ref["staging"]["migration_pairs"]
        assert len(staging["migration_pairs"]) == len(ref["staging"]["migration_pairs"])
        assert staging["preservation_waves"] == ref["staging"]["preservation_waves"]
        assert len(staging["preservation_waves"]) < len(staging["migration_pairs"])
        assert staging["within_storage_budget"] is True
        assert staging["schedule_hash"] == ref["staging"]["schedule_hash"]
        return self

    def assert_manifest_binds_all_layers(self) -> PreservationVerifier:
        manifest = json.loads(INGEST_MANIFEST.read_text())
        snap = json.loads(COLLECTION_SNAPSHOT.read_text())
        pools = json.loads(REDUNDANCY_POOLS.read_text())
        rollup = json.loads(MIGRATION_ROLLUP.read_text())
        ledger = json.loads(INDEX_LEDGER.read_text())
        staging = json.loads(PRESERVATION_STAGING.read_text())
        assert manifest["collection_snapshot_hash"] == snap["collection_snapshot_hash"]
        assert manifest["redundancy_hash"] == pools["redundancy_hash"]
        assert manifest["rollup_hash"] == rollup["rollup_hash"]
        assert manifest["index_digest"] == ledger["index_digest"]
        assert manifest["schedule_hash"] == staging["schedule_hash"]
        assert manifest["ingest_complete"] is True
        return self

    def assert_atlas_and_preservation_report(self) -> PreservationVerifier:
        ref = self.reference()
        atlas = json.loads(PRESERVATION_ATLAS.read_text())
        report = json.loads(PRESERVATION_REPORT.read_text())
        assert atlas["migration_pairs"] == ref["atlas"]["migration_pairs"]
        assert atlas["schedule_hash"] == ref["atlas"]["schedule_hash"]
        assert atlas["collection_label"] == ref["atlas"]["collection_label"]
        assert report["report_fingerprint"] == ref["report"]["report_fingerprint"]
        assert report["artifact_count"] == ref["report"]["artifact_count"]
        assert report["migration_count"] == ref["report"]["migration_count"]
        assert report["wave_count"] == len(atlas["preservation_waves"])
        return self

    def assert_negative_media_slots_preserved(self) -> PreservationVerifier:
        snap = json.loads(COLLECTION_SNAPSHOT.read_text())
        by_id = {e["artifact_id"]: e for e in snap["artifacts"]}
        assert by_id["art-g03"]["media_slot"] == -5
        assert by_id["art-g06"]["media_slot"] == -2
        return self

    def assert_instruction_paths_exist(self) -> PreservationVerifier:
        path_map = {
            "/app/output/preservation-atlas.json": PRESERVATION_ATLAS,
            "/app/output/preservation-report.json": PRESERVATION_REPORT,
            "/app/state/preservation-staging.json": PRESERVATION_STAGING,
            "/app/state/ingest-manifest.json": INGEST_MANIFEST,
            "/app/state/collection-snapshot.json": COLLECTION_SNAPSHOT,
            "/app/state/redundancy-pools.json": REDUNDANCY_POOLS,
            "/app/state/migration-rollup.json": MIGRATION_ROLLUP,
            "/app/state/index-ledger.json": INDEX_LEDGER,
        }
        for cited, actual in path_map.items():
            assert cited in INSTRUCTION_PATHS
            assert actual.exists(), cited
        return self

    def assert_six_state_ledgers(self) -> PreservationVerifier:
        for path in (
            COLLECTION_SNAPSHOT,
            REDUNDANCY_POOLS,
            MIGRATION_ROLLUP,
            INDEX_LEDGER,
            PRESERVATION_STAGING,
            INGEST_MANIFEST,
        ):
            assert path.is_file()
            assert json.loads(path.read_text())["schema_version"] == 1
        return self
