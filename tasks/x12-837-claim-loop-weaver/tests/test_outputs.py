"""
Verifier tests for x12-837-claim-loop-weaver.

Compares /app/claim-weaver output to an independent Python reference weaver.
Adversarial shard inputs are generated at test time from a fixed seed.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

import pytest

from x12_837_reference import build_outputs
from x12_mutate import run_mutate

APP = Path("/app")
BINARY = APP / "claim-weaver"
SHARDS = APP / "data" / "shards"
MANIFEST = APP / "data" / "shard-manifest.json"
CLAIMS_PATH = APP / "output" / "woven-claims.json"
SUMMARY_PATH = APP / "output" / "weave-summary.json"
ERRORS_PATH = APP / "output" / "errors.log"
SNAPSHOT_PATH = APP / "state" / "weave-snapshot.json"
LEDGER_PATH = APP / "state" / "weave-ledger.json"
BASELINE_BACKUP = Path("/tmp/x12-837-baseline-backup")
HIDDEN_CHAIN_DIR = Path("/tests/fixtures/hidden-chain-pipe")
ADV_SEED = os.environ.get("X12_ADV_SEED", str(uuid.uuid4()))

BASELINE_SHA256 = {
    "biller-east.edi": "ed3323236f1f37f1675c1c0bd1f242ce71a2c30e3f6cbf8037058ebc89941a98",
    "biller-west.edi": "f3c45984fcb4ed0792267246371044ab44f541600209bed956bbf500693e00bf",
    "baseline-trailer.edi": "f9294150fd7acdb1ad962aee5b221f261c8ffc9789d12ea07f1bc2524cc225c8",
}


def _fixture_sha256() -> dict[str, str]:
    digests: dict[str, str] = {}
    for name, expected in BASELINE_SHA256.items():
        path = SHARDS / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == expected, f"baseline fixture {name} was modified"
        digests[name] = digest
    return digests


def _clear_state() -> None:
    for path in (SNAPSHOT_PATH, LEDGER_PATH):
        if path.exists():
            path.unlink()


def _rebuild_and_run() -> subprocess.CompletedProcess[str]:
    rebuild = subprocess.run(
        ["/opt/verifier-scripts/rebuild-tool"],
        capture_output=True,
        text=True,
    )
    assert rebuild.returncode == 0, rebuild.stderr
    for path in (CLAIMS_PATH, SUMMARY_PATH, ERRORS_PATH):
        if path.exists():
            path.unlink()
    _clear_state()
    return subprocess.run([str(BINARY)], capture_output=True, text=True)


def _read_agent_outputs() -> tuple[dict, dict, str]:
    claims = json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))
    summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    errors = ERRORS_PATH.read_text(encoding="utf-8")
    return claims, summary, errors


@pytest.fixture(scope="module", autouse=True)
def build_once():
    _clear_state()
    proc = _rebuild_and_run()
    assert proc.returncode in {0, 3}, proc.stderr
    yield


@pytest.fixture
def restore_baseline_env():
    if BASELINE_BACKUP.exists():
        shutil.rmtree(BASELINE_BACKUP)
    shutil.copytree(SHARDS, BASELINE_BACKUP / "shards")
    shutil.copy2(MANIFEST, BASELINE_BACKUP / "shard-manifest.json")
    yield
    shutil.rmtree(SHARDS)
    shutil.copytree(BASELINE_BACKUP / "shards", SHARDS)
    shutil.copy2(BASELINE_BACKUP / "shard-manifest.json", MANIFEST)


class TestCoreCorrectness:
    def test_output_files_exist(self):
        """woven-claims.json, weave-summary.json, and errors.log must be written."""
        assert CLAIMS_PATH.is_file()
        assert SUMMARY_PATH.is_file()
        assert ERRORS_PATH.is_file()

    def test_weave_snapshot_written(self):
        """Ingest stage must persist intermediate state to weave-snapshot.json."""
        assert SNAPSHOT_PATH.is_file()
        snap = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        assert snap.get("version") == 1
        assert isinstance(snap.get("claims"), list)
        assert snap.get("claims"), "snapshot must contain woven claims after ingest"

    def test_ingest_exits_zero_when_segments_skipped(self, restore_baseline_env):
        """claim-weaver ingest must exit 0 even when baseline shards contain skipped segments."""
        _, expected_summary, _, _ = build_outputs(SHARDS, MANIFEST)
        assert expected_summary["skipped_segments"] > 0
        proc = subprocess.run([str(BINARY), "ingest"], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        assert SNAPSHOT_PATH.is_file()

    def test_snapshot_manifest_fingerprint_after_ingest(self, restore_baseline_env):
        """Ingest must record manifest_fingerprint as SHA-256 of raw shard-manifest.json bytes."""
        expected = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
        proc = subprocess.run([str(BINARY), "ingest"], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        snap = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        assert snap.get("manifest_fingerprint") == expected

    def test_snapshot_stores_inherited_pointers_at_lx_open(self, restore_baseline_env):
        """Snapshot line rows must capture inherited_pointers at LX open for reconcile export."""
        proc = subprocess.run([str(BINARY), "ingest"], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        snap = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        clm100 = next(item for item in snap["claims"] if item["control_number"] == "CLM100")
        line2 = clm100["lines"]["2"]
        assert line2.get("inherited_pointers") == ["1"]

    def test_baseline_woven_claims_match_reference(self):
        """Shipped shard fixtures must match the independent loop weaver reference."""
        _fixture_sha256()
        expected_claims, expected_summary, _, _ = build_outputs(SHARDS, MANIFEST)
        actual_claims, actual_summary, _ = _read_agent_outputs()
        assert actual_claims == expected_claims
        assert actual_summary == expected_summary

    def test_pipe_separator_shard_parsed(self):
        """biller-west.edi uses pipe element separators from its ISA header."""
        _fixture_sha256()
        actual_claims, _, _ = _read_agent_outputs()
        controls = {claim["control_number"] for claim in actual_claims["claims"]}
        assert "CLM200" in controls

    def test_service_line_lx_ordering(self):
        """Service lines within a claim must be sorted by lx_sequence ascending."""
        expected_claims, _, _, _ = build_outputs(SHARDS, MANIFEST)
        actual_claims, _, _ = _read_agent_outputs()
        for expected in expected_claims["claims"]:
            actual = next(
                item for item in actual_claims["claims"] if item["control_number"] == expected["control_number"]
            )
            lx_values = [line["lx_sequence"] for line in actual["service_lines"]]
            assert lx_values == sorted(lx_values)

    def test_diagnosis_pointer_inheritance_on_second_line(self):
        """LX line without HI must inherit diagnosis pointers from the prior 2400 loop."""
        expected_claims, _, _, _ = build_outputs(SHARDS, MANIFEST)
        actual_claims, _, _ = _read_agent_outputs()
        assert actual_claims == expected_claims
        clm100 = next(item for item in actual_claims["claims"] if item["control_number"] == "CLM100")
        assert len(clm100["service_lines"]) == 2
        second = clm100["service_lines"][1]
        assert second["diagnosis_pointers"] == ["1"]

    def test_idempotent_output_bytes(self):
        """Re-running on unchanged inputs must produce byte-identical output files."""
        _fixture_sha256()
        claims_bytes = CLAIMS_PATH.read_bytes()
        summary_bytes = SUMMARY_PATH.read_bytes()
        errors_bytes = ERRORS_PATH.read_bytes()
        proc = subprocess.run([str(BINARY)], capture_output=True, text=True)
        assert proc.returncode in {0, 3}, proc.stderr
        assert CLAIMS_PATH.read_bytes() == claims_bytes
        assert SUMMARY_PATH.read_bytes() == summary_bytes
        assert ERRORS_PATH.read_bytes() == errors_bytes

    def test_export_summary_manifest_fingerprint_from_validate(self, restore_baseline_env):
        """Validate stage must echo snapshot manifest_fingerprint into weave-summary.json."""
        expected_fp = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
        proc = subprocess.run([str(BINARY), "export"], capture_output=True, text=True)
        assert proc.returncode in {0, 3}, proc.stderr
        summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        assert summary.get("manifest_fingerprint") == expected_fp

    def test_ledger_written_after_ingest(self, restore_baseline_env):
        """Ingest must write weave-ledger.json with errors_digest and export_epoch."""
        _clear_state()
        _, expected_summary, _, _ = build_outputs(SHARDS, MANIFEST)
        proc = subprocess.run([str(BINARY), "ingest"], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr
        assert LEDGER_PATH.is_file()
        ledger = json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        assert ledger.get("version") == 1
        assert ledger.get("export_epoch") == 1
        assert ledger.get("errors_digest") == expected_summary["errors_digest"]
        assert ledger.get("manifest_fingerprint") == expected_summary["manifest_fingerprint"]

    def test_export_summary_errors_digest_from_ledger(self, restore_baseline_env):
        """Export validate must copy errors_digest and export_epoch from a matching ledger."""
        expected_claims, expected_summary, _, _ = build_outputs(SHARDS, MANIFEST)
        proc = subprocess.run([str(BINARY), "export"], capture_output=True, text=True)
        assert proc.returncode in {0, 3}, proc.stderr
        summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        assert summary.get("errors_digest") == expected_summary["errors_digest"]
        assert summary.get("export_epoch") == expected_summary["export_epoch"]
        actual_claims, _, _ = _read_agent_outputs()
        assert actual_claims == expected_claims


class TestAdversarialTraps:
    def test_Agent_fails_nbsp_patient_name_normalization(self, restore_baseline_env):
        """
        Trap: ASCII whitespace vs Unicode — U+00A0 in NM103 must normalize to 'SMITH JOHN'.
        """
        _rebuild_and_run()
        claims, _, _ = _read_agent_outputs()
        clm100 = next(item for item in claims["claims"] if item["control_number"] == "CLM100")
        assert clm100["patient_name"] == "SMITH JOHN"

    def test_Agent_fails_malformed_segment_preserved_in_errors_log(self, restore_baseline_env):
        """
        Trap: malformed input logging — errors.log must preserve the raw skipped segment text.
        """
        _, _, expected_errors, _ = build_outputs(SHARDS, MANIFEST)
        _rebuild_and_run()
        _, _, actual_errors = _read_agent_outputs()
        assert "NM1|XX|1|BAD|NAME||||MI|BAD001" in actual_errors
        for line in expected_errors:
            assert line in actual_errors

    def test_Agent_fails_errors_log_lines_sorted_alphabetically(self, restore_baseline_env):
        """
        Trap: errors.log contract — skipped-segment lines must be sorted lexicographically.
        """
        _, _, expected_errors, _ = build_outputs(SHARDS, MANIFEST)
        assert len(expected_errors) > 1
        _rebuild_and_run()
        _, _, actual_errors = _read_agent_outputs()
        lines = [line for line in actual_errors.splitlines() if line]
        assert lines == sorted(lines)
        assert lines == sorted(expected_errors)

    def test_Agent_fails_export_errors_from_snapshot_after_shard_mutation(self, restore_baseline_env):
        """
        Trap: export must write errors.log from the frozen snapshot, not re-parse mutated shards.
        """
        ingest = subprocess.run([str(BINARY), "ingest"], capture_output=True, text=True)
        assert ingest.returncode == 0, ingest.stderr
        snap = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        baseline_errors = list(snap.get("errors", []))

        west = SHARDS / "biller-west.edi"
        west.write_text(west.read_text(encoding="utf-8") + "NM1|XX|1|EXTRA|BAD||||MI|BAD002~", encoding="utf-8")

        export_only = subprocess.run([str(BINARY), "export"], capture_output=True, text=True)
        assert export_only.returncode in {0, 3}, export_only.stderr
        _, _, actual_errors = _read_agent_outputs()
        actual_lines = [line for line in actual_errors.splitlines() if line]
        assert actual_lines == sorted(baseline_errors)
        assert "BAD002" not in actual_errors

    def test_Agent_fails_exit_code_three_on_skipped_segments(self, restore_baseline_env):
        """
        Trap: exit code precision — skipped segments must yield exit 3 while still writing outputs.
        """
        _, expected_summary, _, _ = build_outputs(SHARDS, MANIFEST)
        assert expected_summary["skipped_segments"] > 0
        proc = _rebuild_and_run()
        assert proc.returncode == 3, proc.stderr
        assert CLAIMS_PATH.is_file()
        assert SUMMARY_PATH.is_file()

    def test_Agent_fails_frequency_supersession_removes_prior_claim(self, restore_baseline_env):
        """
        Trap: implicit rule interaction — CLM200 freq 7 + REF*F8 must remove CLM100 from output.
        """
        west = SHARDS / "biller-west.edi"
        body = west.read_text(encoding="utf-8")
        body = body.replace("11:B:1", "11:B:7", 1)
        body = body.replace(
            "CLM|CLM200|150.00|||11:B:7|Y*A*Y*Y~",
            "CLM|CLM200|150.00|||11:B:7|Y*A*Y*Y~\nREF|F8|CLM100~",
            1,
        )
        west.write_text(body, encoding="utf-8")
        expected_claims, _, _, _ = build_outputs(SHARDS, MANIFEST)
        _rebuild_and_run()
        actual_claims, _, _ = _read_agent_outputs()
        controls = {claim["control_number"] for claim in actual_claims["claims"]}
        assert "CLM100" not in controls
        assert actual_claims == expected_claims

    def test_Agent_fails_summary_counts_post_supersession(self, restore_baseline_env):
        """
        Trap: weave-summary.json claim_count and service_line_count must match survivors after supersession.
        """
        west = SHARDS / "biller-west.edi"
        body = west.read_text(encoding="utf-8")
        body = body.replace("11:B:1", "11:B:7", 1)
        body = body.replace(
            "CLM|CLM200|150.00|||11:B:7|Y*A*Y*Y~",
            "CLM|CLM200|150.00|||11:B:7|Y*A*Y*Y~\nREF|F8|CLM100~",
            1,
        )
        west.write_text(body, encoding="utf-8")
        expected_claims, expected_summary, _, _ = build_outputs(SHARDS, MANIFEST)
        _rebuild_and_run()
        actual_claims, actual_summary, _ = _read_agent_outputs()
        assert actual_summary == expected_summary
        assert actual_claims == expected_claims

    def test_Agent_fails_chained_frequency_supersession(self, restore_baseline_env):
        """
        Trap: chained freq-7 replacement claims must remove every superseded control number.
        """
        west = SHARDS / "biller-west.edi"
        body = west.read_text(encoding="utf-8")
        body = body.replace("11:B:1", "11:B:7", 1)
        body = body.replace(
            "CLM|CLM200|150.00|||11:B:7|Y*A*Y*Y~",
            "CLM|CLM200|150.00|||11:B:7|Y*A*Y*Y~\nREF|F8|CLM100~\nCLM|CLM300|99.00|||11:B:7|Y*A*Y*Y~\nREF|F8|CLM200~",
            1,
        )
        west.write_text(body, encoding="utf-8")
        expected_claims, expected_summary, _, _ = build_outputs(SHARDS, MANIFEST)
        _rebuild_and_run()
        actual_claims, actual_summary, _ = _read_agent_outputs()
        controls = {claim["control_number"] for claim in actual_claims["claims"]}
        assert controls == {"CLM300"}
        assert actual_claims == expected_claims
        assert actual_summary == expected_summary

    def test_Agent_fails_export_without_reingest_after_shard_mutation(self, restore_baseline_env):
        """
        Trap: cross-stage poison pill — export alone must not reflect mutated shards;
        ingest must run after shard changes before export matches reference.
        """
        west = SHARDS / "biller-west.edi"
        body = west.read_text(encoding="utf-8")
        body = body.replace("11:B:1", "11:B:7", 1)
        body = body.replace(
            "CLM|CLM200|150.00|||11:B:7|Y*A*Y*Y~",
            "CLM|CLM200|150.00|||11:B:7|Y*A*Y*Y~\nREF|F8|CLM100~",
            1,
        )
        west.write_text(body, encoding="utf-8")
        expected_claims, _, _, _ = build_outputs(SHARDS, MANIFEST)
        export_only = subprocess.run([str(BINARY), "export"], capture_output=True, text=True)
        assert export_only.returncode in {0, 3}, export_only.stderr
        stale_claims, _, _ = _read_agent_outputs()
        assert stale_claims != expected_claims
        ingest = subprocess.run([str(BINARY), "ingest"], capture_output=True, text=True)
        assert ingest.returncode == 0, ingest.stderr
        export_fresh = subprocess.run([str(BINARY), "export"], capture_output=True, text=True)
        assert export_fresh.returncode in {0, 3}, export_fresh.stderr
        actual_claims, _, _ = _read_agent_outputs()
        assert actual_claims == expected_claims

    def test_Agent_fails_seed_lx_shuffle_ordering(self, restore_baseline_env):
        """
        Trap: seed-based mutated fixtures — shuffled LX segments must still sort by lx_sequence.
        """
        for shard in SHARDS.glob("*.edi"):
            shard.unlink()
        run_mutate(ADV_SEED, SHARDS)
        expected_claims, expected_summary, _, _ = build_outputs(SHARDS, MANIFEST)
        proc = _rebuild_and_run()
        assert proc.returncode == 0, proc.stderr
        actual_claims, actual_summary, _ = _read_agent_outputs()
        adv100 = next(item for item in actual_claims["claims"] if item["control_number"] == "ADV100")
        lx_values = [line["lx_sequence"] for line in adv100["service_lines"]]
        assert lx_values == [1, 2]
        assert actual_claims == expected_claims
        assert actual_summary == expected_summary

    def test_hidden_validate_post_supersession_line_count(self, restore_baseline_env):
        """
        Trap: hidden fixture — validate stage must set service_line_count after supersession;
        compose+supersede alone leave pre-supersession totals that fail on hidden input.
        """
        for shard in SHARDS.glob("*.edi"):
            shard.unlink()
        shutil.copy2(HIDDEN_CHAIN_DIR / "hidden-chain.edi", SHARDS / "hidden-chain.edi")
        shutil.copy2(HIDDEN_CHAIN_DIR / "shard-manifest.json", MANIFEST)
        expected_claims, expected_summary, _, _ = build_outputs(SHARDS, MANIFEST)
        assert expected_summary["service_line_count"] == 1
        proc = _rebuild_and_run()
        assert proc.returncode == 0, proc.stderr
        actual_claims, actual_summary, _ = _read_agent_outputs()
        controls = {claim["control_number"] for claim in actual_claims["claims"]}
        assert controls == {"HCLM200"}
        assert actual_summary["service_line_count"] == 1
        assert actual_claims == expected_claims
        assert actual_summary == expected_summary

    def test_tb3_isolated_state_requires_ledger_for_export_summary(self, restore_baseline_env):
        """
        Trap: TB3_WEAVE_STATE absolute dir — export validate must read ledger from the same
        state directory; snapshot without ledger leaves summary digest fields empty.
        """
        isolated = Path("/tmp/tb3-weave-state-x12")
        if isolated.exists():
            shutil.rmtree(isolated)
        isolated.mkdir(parents=True)
        env = {**os.environ, "TB3_WEAVE_STATE": str(isolated)}
        ingest = subprocess.run([str(BINARY), "ingest"], capture_output=True, text=True, env=env)
        assert ingest.returncode == 0, ingest.stderr
        snap_path = isolated / "weave-snapshot.json"
        ledger_path = isolated / "weave-ledger.json"
        assert snap_path.is_file()
        assert ledger_path.is_file()
        ledger_path.unlink()
        export = subprocess.run([str(BINARY), "export"], capture_output=True, text=True, env=env)
        assert export.returncode in {0, 3}, export.stderr
        _, expected_summary, _, _ = build_outputs(SHARDS, MANIFEST)
        summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
        assert summary.get("errors_digest") != expected_summary["errors_digest"]
