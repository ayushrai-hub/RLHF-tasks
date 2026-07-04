"""Verification for edge device drift classification auditor."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

REPORT_PATH = Path("/app/build/drift_audit_report.json")
REPORT_FIRST = Path("/logs/verifier/report_first.json")
VERIFIER_DIR = Path("/logs/verifier")
BASELINE_DIR = Path("/opt/verifier-baseline")
FIXTURES = Path("/app/fixtures")
MANIFEST = FIXTURES / "manifest.json"
APP = Path("/app")

DRIFT_KINDS = frozenset({
    "FEATURE_SCALE_DRIFT",
    "QUANT_MISMATCH",
    "STALE_CALIBRATION",
    "METADATA_CORRUPT",
    "REGION_DIVERGENCE",
    "DUPLICATE_SAMPLE",
    "UNKNOWN_REGION",
    "MISSING_MODEL",
    "OUT_OF_RANGE_QUANT",
    "CLASS_COLLISION",
})

FLAG_ID_RE = __import__("re").compile(r"^[^:]+::[^:]+::[^:]+::\d{4}$")
IMMUTABLE_SHA256: dict[str, str] = {}

SCENARIO_KEYS = (
    "consistency_hash",
    "drift_flags",
    "duplicate_events_skipped",
    "model_version",
    "regions",
    "scenario_id",
    "status",
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_make(target: str, log_name: str) -> None:
    VERIFIER_DIR.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(["make", target], cwd=APP, capture_output=True, text=True)
    (VERIFIER_DIR / log_name).write_text(proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        pytest.fail(f"make {target} failed; see /logs/verifier/{log_name}")


def _set_fixtures_writable(writable: bool) -> None:
    """Allow verifier perturb/restore on read-only fixture tree."""
    flag = "u+w" if writable else "a-w"
    subprocess.run(["chmod", "-R", flag, str(FIXTURES)], check=False)


def _nums(values: list[Any]) -> list[float]:
    """Normalize numeric lists for int versus float JSON encoding."""
    return [float(v) for v in values]


def _expected_consistency_hash(row: dict[str, Any]) -> str:
    """sha256 hex of sorted inference records per rule_catalog consistency_hash."""
    entries: list[dict[str, Any]] = []
    for region in row["regions"]:
        for sample in region["samples"]:
            if sample["probabilities"]:
                entries.append({
                    "predicted_class": sample["predicted_class"],
                    "region_id": region["region_id"],
                    "sample_id": sample["sample_id"],
                })
    entries.sort(key=lambda item: (item["sample_id"], item["region_id"]))
    raw = json.dumps(entries, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _row(report: dict[str, Any], sid: str) -> dict[str, Any]:
    for row in report["scenarios"]:
        if row["scenario_id"] == sid:
            return row
    raise KeyError(sid)


def _assert_keys_alphabetical(obj: Any, path: str = "report") -> None:
    """Every JSON object in the report must use strict alphabetical key order."""
    if isinstance(obj, dict):
        keys = list(obj.keys())
        assert keys == sorted(keys), f"keys not alphabetical at {path}: {keys}"
        for key, value in obj.items():
            _assert_keys_alphabetical(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            _assert_keys_alphabetical(item, f"{path}[{index}]")


def _perturb_scenario_01() -> None:
    _set_fixtures_writable(True)
    path = FIXTURES / "scenario_01.json"
    obj = json.loads(path.read_text(encoding="utf-8"))
    shutil.copy(path, VERIFIER_DIR / "scenario_01_clean.json")
    for ev in obj["events"]:
        if ev.get("kind") == "RUN_INFERENCE" and ev.get("region_id") == "us-east":
            ev["logits"] = [2.0, 0.0]
            break
    else:
        raise RuntimeError("perturb target missing")
    path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")


@pytest.fixture(scope="session", autouse=True)
def _grading_setup() -> None:
    VERIFIER_DIR.mkdir(parents=True, exist_ok=True)
    for name in ("report_first.json", "scenario_01_clean.json"):
        (VERIFIER_DIR / name).unlink(missing_ok=True)
    for path in VERIFIER_DIR.glob("*.log"):
        path.unlink()

    _perturb_scenario_01()
    REPORT_PATH.unlink(missing_ok=True)
    _run_make("build", "build.log")
    _run_make("audit", "audit.log")
    if not REPORT_PATH.is_file():
        pytest.fail("drift_audit_report.json missing after perturbed audit")
    shutil.copy(REPORT_PATH, REPORT_FIRST)
    _run_make("audit", "audit2.log")
    if REPORT_PATH.read_bytes() != REPORT_FIRST.read_bytes():
        pytest.fail("perturbed rerun not byte-identical")

    _set_fixtures_writable(True)
    shutil.copy(VERIFIER_DIR / "scenario_01_clean.json", FIXTURES / "scenario_01.json")
    _set_fixtures_writable(False)
    REPORT_PATH.unlink(missing_ok=True)
    _run_make("audit", "audit_restore.log")
    shutil.copy(REPORT_PATH, REPORT_FIRST)
    _run_make("audit", "audit_restore2.log")
    if REPORT_PATH.read_bytes() != REPORT_FIRST.read_bytes():
        pytest.fail("restored rerun not byte-identical")


@pytest.fixture(scope="session", autouse=True)
def _capture_immutable(_grading_setup: None) -> None:
    if IMMUTABLE_SHA256:
        return
    assert BASELINE_DIR.is_dir(), f"missing verifier baseline {BASELINE_DIR}"
    for rel in ("Makefile", "go.mod"):
        IMMUTABLE_SHA256[rel] = _sha256_file(BASELINE_DIR / rel)
    for sub in ("fixtures", "spec", "assets"):
        for path in sorted((BASELINE_DIR / sub).rglob("*")):
            if path.is_file():
                IMMUTABLE_SHA256[path.relative_to(BASELINE_DIR).as_posix()] = _sha256_file(path)


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    assert REPORT_PATH.is_file(), f"missing {REPORT_PATH}"
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def test_solution_contract_integrity(report: dict[str, Any]) -> None:
    """Immutability, manifest order, schema keys, alphabetical JSON keys, compact determinism."""
    assert BASELINE_DIR.is_dir(), "verifier-owned baseline missing"
    for path in APP.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(APP).as_posix()
        if rel.startswith(("bin/", "engine/", "build/")):
            continue
        assert rel in IMMUTABLE_SHA256, f"untracked path {rel}"
        assert _sha256_file(path) == IMMUTABLE_SHA256[rel], f"modified {rel}"

    expected = [f"scenario_{i:02d}" for i in range(1, 66)]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["scenarios"] == expected
    assert [r["scenario_id"] for r in report["scenarios"]] == expected

    for row in report["scenarios"]:
        assert list(row.keys()) == list(SCENARIO_KEYS)
        assert set(row.keys()) == set(SCENARIO_KEYS)
        if row["drift_flags"]:
            assert row["status"] == "DRIFT_DETECTED", (
                f"{row['scenario_id']} with flags must use DRIFT_DETECTED not {row['status']!r}"
            )
        else:
            assert row["status"] == "CONSISTENT", (
                f"{row['scenario_id']} with no flags must use CONSISTENT not {row['status']!r}"
            )
        for fl in row["drift_flags"]:
            assert FLAG_ID_RE.match(fl["flag_id"])
            assert fl["kind"] in DRIFT_KINDS

    _assert_keys_alphabetical(report)

    raw = REPORT_PATH.read_bytes()
    assert raw.endswith(b"\n") and b": " not in raw and b", " not in raw
    assert b"null" not in raw, "json must use empty arrays not null for drift_flags and feature fields"
    canonical = json.dumps(
        report, separators=(",", ":"), ensure_ascii=False, sort_keys=True,
    ).encode() + b"\n"
    assert raw == canonical
    assert REPORT_FIRST.is_file() and raw == REPORT_FIRST.read_bytes()
    assert not (APP / "driftaudit").exists()
    assert (APP / "build" / "driftaudit").is_file()


def test_stale_calibration_detail_is_version(report: dict[str, Any]) -> None:
    """scenario_04 STALE_CALIBRATION detail must be the SET_CALIBRATION version v0."""
    row = _row(report, "scenario_04")
    stale = next(f for f in row["drift_flags"] if f["kind"] == "STALE_CALIBRATION")
    assert stale["detail"] == "v0"
    assert stale["flag_id"] == "scenario_04::us-east::_::0003"


def test_dual_quant_flags_per_channel(report: dict[str, Any]) -> None:
    """scenario_45 one QUANTIZE_SAMPLE may emit OUT_OF_RANGE_QUANT and QUANT_MISMATCH per channel."""
    row = _row(report, "scenario_45")
    out = next(f for f in row["drift_flags"] if f["kind"] == "OUT_OF_RANGE_QUANT")
    mismatches = sorted(
        f["detail"] for f in row["drift_flags"] if f["kind"] == "QUANT_MISMATCH"
    )
    assert out["detail"] == "127"
    assert mismatches == ["0", "1"]
    assert out["event_seq"] == 4


def test_policy_override_disables_stale_calibration(report: dict[str, Any]) -> None:
    """scenario_28 policy_overrides calibration_gate false must suppress STALE_CALIBRATION."""
    row = _row(report, "scenario_28")
    assert not any(f["kind"] == "STALE_CALIBRATION" for f in row["drift_flags"])
    assert row["drift_flags"] == []


def test_weights_digest_and_inference_without_lock_row(report: dict[str, Any]) -> None:
    """scenario_58 digest compares ASCII hex; RUN_INFERENCE without lock still emits sample s9."""
    row = _row(report, "scenario_58")
    corrupt = next(f for f in row["drift_flags"] if f["kind"] == "METADATA_CORRUPT")
    assert corrupt["detail"] == "wrongdigest"
    assert corrupt["flag_id"] == "scenario_58::_::_::0001"
    assert row["model_version"] == "v1"
    sample = next(s for r in row["regions"] for s in r["samples"] if s["sample_id"] == "s9")
    assert sample["predicted_class"] == 0
    assert sample["normalized_features"] == []
    assert sample["probabilities"]


def test_post_audit_after_skipped_duplicate(report: dict[str, Any]) -> None:
    """scenario_32 skipped duplicate at max seq still post-audits at max seq plus one."""
    row = _row(report, "scenario_32")
    assert row["duplicate_events_skipped"] == 1
    div = next(f for f in row["drift_flags"] if f["kind"] == "REGION_DIVERGENCE")
    assert div["event_seq"] == 11
    assert div["detail"] == "1,us-east"
    assert div["flag_id"] == "scenario_32::us-east::s1::0011"


def test_same_region_dual_post_audit_flags(report: dict[str, Any]) -> None:
    """scenario_47 us-east must receive both REGION_DIVERGENCE and FEATURE_SCALE_DRIFT."""
    row = _row(report, "scenario_47")
    us_east = [f for f in row["drift_flags"] if f["region_id"] == "us-east"]
    assert {f["kind"] for f in us_east} == {"REGION_DIVERGENCE", "FEATURE_SCALE_DRIFT"}
    div = next(f for f in us_east if f["kind"] == "REGION_DIVERGENCE")
    drift = next(f for f in us_east if f["kind"] == "FEATURE_SCALE_DRIFT")
    assert div["detail"] == "0,us-east"
    assert drift["detail"] == "eu-west"


def test_equal_seq_dedup_keeps_lexicographic_region(report: dict[str, Any]) -> None:
    """scenario_50 equal seq dedup must keep eu-west lock and skip us-east body."""
    row = _row(report, "scenario_50")
    assert row["duplicate_events_skipped"] == 1
    sample = next(s for r in row["regions"] if r["region_id"] == "eu-west" for s in r["samples"])
    assert sample["normalized_features"][0] == pytest.approx(100.0, rel=1e-9, abs=1e-9)


def test_duplicate_rejected_lock_preserves_welford(report: dict[str, Any]) -> None:
    """scenario_24 rejected DUPLICATE_SAMPLE must not poison later Welford normalization."""
    row = _row(report, "scenario_24")
    dup = next(f for f in row["drift_flags"] if f["kind"] == "DUPLICATE_SAMPLE")
    assert dup["detail"] == "s1"
    s2 = next(s for r in row["regions"] for s in r["samples"] if s["sample_id"] == "s2")
    assert s2["normalized_features"][0] == pytest.approx(4_000_000.0, rel=1e-6, abs=1e-3)


def test_agreeing_classes_skip_region_divergence(report: dict[str, Any]) -> None:
    """scenario_53 identical predicted_class must emit FEATURE_SCALE_DRIFT only."""
    row = _row(report, "scenario_53")
    assert "REGION_DIVERGENCE" not in {f["kind"] for f in row["drift_flags"]}
    drift = next(f for f in row["drift_flags"] if f["kind"] == "FEATURE_SCALE_DRIFT")
    assert drift["region_id"] == "us-east"
    assert drift["detail"] == "eu-west"


def test_set_calibration_before_region_register(report: dict[str, Any]) -> None:
    """scenario_56 SET_CALIBRATION before REGISTER_REGION must still apply stored temperature."""
    row = _row(report, "scenario_56")
    sample = row["regions"][0]["samples"][0]
    proc = subprocess.run(
        ["node", str(APP / "assets" / "calibrate.js"), "0.25", "1.0", "1.0"],
        capture_output=True,
        text=True,
        check=True,
    )
    expected = json.loads(proc.stdout)
    for got, want in zip(_nums(sample["probabilities"]), expected, strict=True):
        assert got == pytest.approx(want, rel=1e-9, abs=1e-9)


def test_l2_strict_threshold_suppresses_drift(report: dict[str, Any]) -> None:
    """scenario_29 normalized L2 exactly 0.5 must emit no post-replay drift flags."""
    row = _row(report, "scenario_29")
    assert row["drift_flags"] == []


def test_multi_region_unlocked_inference_hash(report: dict[str, Any]) -> None:
    """scenario_64 unlocked multi-region inference must hash both regions in sorted order."""
    row = _row(report, "scenario_64")
    assert row["consistency_hash"] == _expected_consistency_hash(row)
    samples = [s for r in row["regions"] for s in r["samples"] if s["sample_id"] == "s9"]
    assert len(samples) == 2
    assert {s["predicted_class"] for s in samples} == {0, 1}


def test_equal_seq_register_before_lock(report: dict[str, Any]) -> None:
    """scenario_65 equal seq must process REGISTER_REGION before LOCK_SAMPLE."""
    row = _row(report, "scenario_65")
    assert not any(f["kind"] == "UNKNOWN_REGION" for f in row["drift_flags"])
    sample = row["regions"][0]["samples"][0]
    assert sample["normalized_features"][0] == pytest.approx(8.0, rel=1e-9, abs=1e-9)
    assert sample["probabilities"]
