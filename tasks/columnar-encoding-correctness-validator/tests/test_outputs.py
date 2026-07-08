"""Verifier for the columnar encoding correctness validator task."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

import yaml

REPORT = Path("/app/output/encoding_integrity_report.json")
REPORT_FIRST = Path("/tmp/encoding_report_first.json")
REPORT_SECOND = Path("/tmp/encoding_report_second.json")
BIN = Path("/app/bin/columnar-validator")
RECONCILE_GO = Path("/app/codec/reconcile/reconcile.go")
FIXTURES = Path("/app/fixtures")
RULES = Path("/app/rules/encoding_policy.yaml")
REPORT_SPEC = Path("/app/spec/REPORT_SPEC.md")
SEGMENT_FORMAT = Path("/app/spec/SEGMENT_FORMAT.md")
STUB_TOKEN = "reconcile.ValidateSegment not implemented"

BUNDLED_FIXTURE_CHECKSUMS: dict[str, str] = {
    "segment_01.json": "db35c78713a136dc3361d4e622defdd108918bb3390d7bba6f872f21b0c13893",
    "segment_02.json": "d7e1c1c1369ca8dfb26c61375ff59ffcc0a2dcfb83b59e65ce61a98e58dcb930",
    "segment_03.json": "b81e6908d77c826797e2ac9754e402dab4aa38771470194976cc71231074f174",
    "segment_04.json": "7388133be4009958b30aa92cfd1c201fd81c60c6b29886c0f4d2d43165fbf2ca",
    "segment_05.json": "cce4d322f2fcd3e0139128fcb073d2d5f7b9f8e022e85a310e870039ec06c5f7",
    "segment_06.json": "61ce789bee1051cee4ec731b370cf9520aab6832b768836e6ee4cfd0eed594c9",
    "segment_07.json": "753fce11d744728bda03753a2c1e1a118e39ff67654d4a322694ff7c7c5df46b",
    "segment_08.json": "e5fbb0310a5bcfe5917a9ef8f8abe414307bca31902f0ee8c4b3259a8a38b427",
    "segment_09.json": "fd0d7941fc735e570fe6b9f068b4361f1d1b6053a2f6d6b308d7ba4b75df5d09",
    "segment_10.json": "83782d1e0b86b31b4c53a604445ad145ba98f9ffd2f3e3d79abe049788aa301d",
    "segment_11.json": "27bd6d1c51d1ecc99cda39048199b9320e2c4a3aed81f9940c540959ad142908",
    "segment_12.json": "bb092889b5571d4af0088ac06619d68c32f34f4fe2ee20b3ac3720fc2190a504",
    "segment_13.json": "d890c602e97fdcb9ccf55326cd04c379a88bf22058ac826ffed91c38b08b0305",
    "segment_14.json": "983b69b1e15cc07b8ea57bd08e7180af201914e2907ace9fda102dca42cceaa5",
    "segment_15.json": "bfb9190b352d95f24fd118d826c26d91644d114b297970157605bf2ba9d59576",
    "segment_16.json": "2b84fe7da580415ca49b9cbd71f02fc1e3dc4ee1aae4744ab4d0e6a84b937ea5",
    "segment_17.json": "3347604c6098642d476f3d2c1a484c40b75851d845a1cb1e3dd6f667230bd365",
    "segment_18.json": "579e10560be081427744e601784071643dcaec03f8b20d02493faf438a143ed9",
    "segment_19.json": "ea2d77b064fedf0a15e2f86f57a09d98183985f4778168ad292edebbf23e70eb",
    "segment_20.json": "47b9ed4ba952f7cafe402c9cbae7916c46e5cb27e9bc90fc467bc45d037a0a21",
}

EXPECTED_REPORT_FINGERPRINT = (
    "d3cd2ffff6db8ed2531fd3ba60617262eb2972ab1f4c81eb4028639e6edc6434"
)

EXPECTED_FAULT_SIGNATURES: dict[str, list[str]] = {
    "segment_02": ["DICT_INDEX_OOB"],
    "segment_03": ["RLE_LENGTH_MISMATCH"],
    "segment_04": ["STATS_DRIFT"],
    "segment_05": ["COLUMN_ROW_MISMATCH"],
    "segment_06": ["PAGE_CORRUPTION"],
    "segment_07": ["DICT_INCREMENTAL_STALE"],
    "segment_08": ["MERGE_ORDER_BROKEN"],
    "segment_09": ["ROW_GROUP_DRIFT"],
    "segment_10": ["DECODE_DIVERGENCE"],
    "segment_11": ["PRUNE_COUNT_WRONG"],
    "segment_12": ["STALE_METADATA"],
    "segment_13": ["SCHEMA_EVOLUTION_GAP"],
    "segment_14": ["PARALLEL_SLOT_COLLISION"],
    "segment_15": ["NULL_BITMAP_MISMATCH"],
    "segment_16": ["BITPACK_OVERFLOW"],
    "segment_17": ["DELTA_BASE_WRONG"],
    "segment_18": ["MERGE_ORDER_BROKEN"],
    "segment_19": ["DICT_INDEX_OOB", "STATS_DRIFT"],
}

CLEAN_SEGMENTS = {"segment_01", "segment_20"}

SUMMARY_KEYS = [
    "segments_analyzed",
    "segments_passing",
    "segments_failing",
    "fault_code_totals",
]

SEGMENT_KEYS = [
    "segment_id",
    "integrity_pass",
    "fault_codes",
    "decoded_row_count",
    "reconstruction_hash_hex",
]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def prepare_verifier_artifacts() -> None:
    """Build and run the validator twice before pytest assertions."""
    if STUB_TOKEN in RECONCILE_GO.read_text(encoding="utf-8"):
        raise AssertionError("reconcile.ValidateSegment is still the shipped stub")

    build = subprocess.run(
        ["make", "build"],
        cwd="/app",
        capture_output=True,
        text=True,
        check=False,
    )
    if build.returncode != 0:
        raise AssertionError(f"make build failed:\n{build.stdout}\n{build.stderr}")

    if not BIN.exists():
        raise AssertionError(f"missing binary {BIN}")
    if BIN.stat().st_size <= 2048:
        raise AssertionError("columnar-validator binary must exceed 2048 bytes")

    for label, dest in (("first", REPORT_FIRST), ("second", REPORT_SECOND)):
        run = subprocess.run(
            [str(BIN)],
            cwd="/app",
            capture_output=True,
            text=True,
            check=False,
        )
        if run.returncode != 0:
            raise AssertionError(f"validator run ({label}) failed: {run.stderr}")
        if not REPORT.exists():
            raise AssertionError(f"missing report after {label} run")
        dest.write_bytes(REPORT.read_bytes())


def _load_report() -> dict:
    prepare_verifier_artifacts()
    return json.loads(REPORT.read_text(encoding="utf-8"))


def _report_text() -> str:
    prepare_verifier_artifacts()
    return REPORT.read_text(encoding="utf-8")


def _segment_map(report: dict) -> dict[str, dict]:
    return {row["segment_id"]: row for row in report["segments"]}


def test_bundled_fixtures_immutable_and_complete() -> None:
    """Bundled fixture files must remain byte-identical and numbered segment_01 through segment_20."""
    names = sorted(BUNDLED_FIXTURE_CHECKSUMS)
    assert names == [f"segment_{i:02d}.json" for i in range(1, 21)]
    extras = list(FIXTURES.glob("segment_*.json"))
    assert len(extras) == 20
    for name, digest in BUNDLED_FIXTURE_CHECKSUMS.items():
        path = FIXTURES / name
        assert path.exists(), f"missing fixture {name}"
        assert _sha256_file(path) == digest, f"tampered fixture {name}"


def test_shipped_docs_and_policy_immutable() -> None:
    """Normative spec files and encoding policy must not be edited by the agent."""
    assert REPORT_SPEC.exists() and SEGMENT_FORMAT.exists() and RULES.exists()
    policy = yaml.safe_load(RULES.read_text(encoding="utf-8"))
    assert policy["validation"]["dictionary_index_base"] == 0
    assert policy["rle"]["require_full_row_coverage"] is True
    reconcile_src = RECONCILE_GO.read_text(encoding="utf-8")
    assert STUB_TOKEN not in reconcile_src
    assert "BUNDLED_FIXTURE_CHECKSUMS" not in reconcile_src
    assert EXPECTED_REPORT_FINGERPRINT not in reconcile_src


def test_report_schema_key_order_and_trailing_newline() -> None:
    """Report must follow REPORT_SPEC key order and end with a single trailing newline."""
    text = _report_text()
    assert text.endswith("\n") and not text.endswith("\n\n")
    assert re.search(r'^  "summary": \{', text, re.M)
    assert re.search(r'^  "segments": \[', text, re.M)
    top = json.loads(text)
    assert list(top.keys()) == ["summary", "segments"]
    assert list(top["summary"].keys()) == SUMMARY_KEYS
    for row in top["segments"]:
        assert list(row.keys()) == SEGMENT_KEYS
        assert row["fault_codes"] == sorted(row["fault_codes"])


def test_summary_counts_reconcile_with_segment_rows() -> None:
    """Summary passing and failing counts must match per-segment integrity_pass flags."""
    report = _load_report()
    summary = report["summary"]
    segments = report["segments"]
    assert summary["segments_analyzed"] == 20
    assert len(segments) == 20
    passing = sum(1 for s in segments if s["integrity_pass"])
    failing = sum(1 for s in segments if not s["integrity_pass"])
    assert summary["segments_passing"] == passing
    assert summary["segments_failing"] == failing
    assert passing + failing == 20
    totals: dict[str, int] = {}
    for row in segments:
        for code in row["fault_codes"]:
            totals[code] = totals.get(code, 0) + 1
    assert summary["fault_code_totals"] == totals
    assert summary["segments_passing"] == 2
    assert summary["segments_failing"] == 18


def test_clean_segments_pass_without_null_fault_lists() -> None:
    """segment_01 and segment_20 must pass with empty fault_codes arrays, never null."""
    report = _load_report()
    by_id = _segment_map(report)
    for seg_id in sorted(CLEAN_SEGMENTS):
        row = by_id[seg_id]
        assert row["integrity_pass"] is True
        assert row["fault_codes"] == []
        assert row["decoded_row_count"] > 0
        assert re.fullmatch(r"[0-9a-f]{64}", row["reconstruction_hash_hex"])


def test_dictionary_and_rle_fault_signatures() -> None:
    """Dictionary, incremental dictionary, and RLE faults must match bundled signatures."""
    by_id = _segment_map(_load_report())
    for seg_id in ("segment_02", "segment_03", "segment_07"):
        assert by_id[seg_id]["fault_codes"] == EXPECTED_FAULT_SIGNATURES[seg_id]
    assert by_id["segment_02"]["decoded_row_count"] == 3
    assert by_id["segment_03"]["decoded_row_count"] == 4


def test_statistics_page_and_column_alignment_faults() -> None:
    """Statistics drift, page corruption, and column row mismatch must be detected."""
    by_id = _segment_map(_load_report())
    for seg_id in ("segment_04", "segment_05", "segment_06"):
        assert by_id[seg_id]["fault_codes"] == EXPECTED_FAULT_SIGNATURES[seg_id]


def test_metadata_row_group_and_pruning_faults() -> None:
    """Row group drift, stale metadata, and predicate pruning faults must be reported."""
    by_id = _segment_map(_load_report())
    for seg_id in ("segment_09", "segment_11", "segment_12"):
        assert by_id[seg_id]["fault_codes"] == EXPECTED_FAULT_SIGNATURES[seg_id]
    assert by_id["segment_11"]["decoded_row_count"] == 4


def test_decode_divergence_and_schema_evolution() -> None:
    """Mirror plain divergence and missing post-evolution statistics must be flagged."""
    by_id = _segment_map(_load_report())
    assert by_id["segment_10"]["fault_codes"] == ["DECODE_DIVERGENCE"]
    assert by_id["segment_13"]["fault_codes"] == ["SCHEMA_EVOLUTION_GAP"]
    seg13 = json.loads((FIXTURES / "segment_13.json").read_text(encoding="utf-8"))
    assert seg13["schema_version"] == 2


def test_compaction_merge_order_monotonicity() -> None:
    """Non-monotonic compaction offsets must raise MERGE_ORDER_BROKEN on segments 08 and 18."""
    by_id = _segment_map(_load_report())
    for seg_id in ("segment_08", "segment_18"):
        assert by_id[seg_id]["fault_codes"] == ["MERGE_ORDER_BROKEN"]


def test_parallel_encoding_and_null_bitmap_integrity() -> None:
    """Parallel slot collisions and null bitmap mismatches must be isolated faults."""
    by_id = _segment_map(_load_report())
    assert by_id["segment_14"]["fault_codes"] == ["PARALLEL_SLOT_COLLISION"]
    assert by_id["segment_15"]["fault_codes"] == ["NULL_BITMAP_MISMATCH"]


def test_bitpack_delta_and_multi_fault_segments() -> None:
    """Bitpack overflow, delta base validation, and compound faults must match spec."""
    by_id = _segment_map(_load_report())
    assert by_id["segment_16"]["fault_codes"] == ["BITPACK_OVERFLOW"]
    assert by_id["segment_17"]["fault_codes"] == ["DELTA_BASE_WRONG"]
    assert by_id["segment_19"]["fault_codes"] == ["DICT_INDEX_OOB", "STATS_DRIFT"]


def test_segment_order_and_ids_match_fixture_basenames() -> None:
    """segments array must list segment_01 through segment_20 in ascending order."""
    report = _load_report()
    ids = [row["segment_id"] for row in report["segments"]]
    assert ids == [f"segment_{i:02d}" for i in range(1, 21)]
    for row in report["segments"]:
        fixture = FIXTURES / f"{row['segment_id']}.json"
        payload = json.loads(fixture.read_text(encoding="utf-8"))
        assert payload["segment_id"] == row["segment_id"]


def test_report_fingerprint_matches_oracle_reconstruction() -> None:
    """Full report bytes must match the oracle structural fingerprint."""
    text = _report_text()
    assert _sha256_text(text) == EXPECTED_REPORT_FINGERPRINT


def test_deterministic_reruns_and_columnar_fixture_dir_isolation() -> None:
    """Back-to-back runs must be byte-identical; swap fixtures via COLUMNAR_FIXTURE_DIR only."""
    prepare_verifier_artifacts()
    assert REPORT_FIRST.read_bytes() == REPORT_SECOND.read_bytes()
    swap_dir = Path("/tmp/columnar-swap-fixtures")
    swap_dir.mkdir(parents=True, exist_ok=True)
    (swap_dir / "segment_99.json").write_text(
        json.dumps(
            {
                "segment_id": "segment_99",
                "row_count": 1,
                "schema_version": 1,
                "columns": [
                    {
                        "name": "z",
                        "encoding": "plain",
                        "logical_type": "int64",
                        "values": [1],
                    }
                ],
                "pages": [{"page_id": 0, "column": "z", "checksum_hex": "deadbeef00000000"}],
                "statistics": {
                    "z": {"min": 1, "max": 1, "null_count": 0, "distinct_count": 1}
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    for i in range(1, 21):
        src = FIXTURES / f"segment_{i:02d}.json"
        (swap_dir / f"segment_{i:02d}.json").write_bytes(src.read_bytes())

    env = os.environ.copy()
    env["COLUMNAR_FIXTURE_DIR"] = str(swap_dir)
    subprocess.run(["make", "build"], cwd="/app", check=True, capture_output=True)
    proc = subprocess.run([str(BIN)], cwd="/app", env=env, capture_output=True, text=True)
    assert proc.returncode == 0
    swap_report = json.loads(REPORT.read_text(encoding="utf-8"))
    assert len(swap_report["segments"]) == 20
    assert all(row["segment_id"] != "segment_99" for row in swap_report["segments"])
