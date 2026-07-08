"""Verifier tests for the karst dripline capacity arbiter CLI."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

APP_DIR = Path(os.environ.get("APP_DIR", "/app"))
GO_BIN = os.environ.get("GO_BIN", "/usr/local/go/bin/go")


def run_cli(input_dir: Path, output_path: Path) -> subprocess.CompletedProcess[str]:
    """Run the Go CLI against a selected input and output path."""
    return subprocess.run(
        [
            GO_BIN,
            "run",
            "./cmd/dripline",
            "--input",
            str(input_dir),
            "--output",
            str(output_path),
        ],
        cwd=APP_DIR,
        text=True,
        capture_output=True,
        check=False,
    )


def load_report(path: Path) -> dict:
    """Load a JSON report from disk."""
    return json.loads(path.read_text())


def fmt2(value: float) -> str:
    """Format digest numeric values with two decimal places."""
    return f"{float(value):.2f}"


def reason_digest(reasons: list[str]) -> str:
    """Return the digest placeholder for a reason-code list."""
    return ",".join(reasons) if reasons else "-"


def recompute_digest(report: dict) -> str:
    """Recompute the public digest from structured report rows."""
    lines: list[str] = []
    for row in report["accepted_observations"]:
        lines.append(
            "A|{obs_id}|{batch_id}|{sensor_id}|{volume}|{risk}|{reasons}|{source}|{seq}".format(
                obs_id=row["obs_id"],
                batch_id=row["batch_id"],
                sensor_id=row["sensor_id"],
                volume=fmt2(row["volume_ml"]),
                risk=row["risk_band"],
                reasons=reason_digest(row["reason_codes"]),
                source=row["capacity_source"],
                seq=row["sequence_index"],
            )
        )
    for row in report["deferred_observations"]:
        lines.append(
            "D|{obs_id}|{batch_id}|{requested}|{base}|{transfer}|{bonus}|{reasons}|{seq}".format(
                obs_id=row["obs_id"],
                batch_id=row["batch_id"],
                requested=fmt2(row["requested_ml"]),
                base=fmt2(row["remaining_base_ml"]),
                transfer=fmt2(row["available_transfer_ml"]),
                bonus=fmt2(row["available_bonus_ml"]),
                reasons=reason_digest(row["reason_codes"]),
                seq=row["sequence_index"],
            )
        )
    for row in report["quarantine"]:
        lines.append(
            f"Q|{row['record_id']}|{row['obs_id']}|{row['code']}|{row['detail']}"
        )
    for row in report["batch_summary"]:
        risks = row["risk_counts"]
        lines.append(
            "B|{batch}|{capacity}|{tin}|{tout}|{bonus}|{base_used}|{transfer_used}|{bonus_used}|"
            "{accepted}|{deferred}|{normal}/{watch}/{critical}".format(
                batch=row["batch_id"],
                capacity=fmt2(row["capacity_ml"]),
                tin=fmt2(row["transfer_in_ml"]),
                tout=fmt2(row["transfer_out_ml"]),
                bonus=fmt2(row["bonus_granted_ml"]),
                base_used=fmt2(row["base_used_ml"]),
                transfer_used=fmt2(row["transfer_used_ml"]),
                bonus_used=fmt2(row["bonus_used_ml"]),
                accepted=row["accepted_count"],
                deferred=row["deferred_count"],
                normal=risks["normal"],
                watch=risks["watch"],
                critical=risks["critical"],
            )
        )
    for row in report["transfer_summary"]:
        lines.append(
            "T|{transfer}|{source}|{target}|{requested}|{moved}|{consumed}|{status}".format(
                transfer=row["transfer_id"],
                source=row["source_batch_id"],
                target=row["target_batch_id"],
                requested=fmt2(row["requested_ml"]),
                moved=fmt2(row["transferred_ml"]),
                consumed=fmt2(row["consumed_ml"]),
                status=row["status"],
            )
        )
    for row in report["chamber_summary"]:
        lines.append(
            "C|{chamber}|{volume}|{accepted}|{deferred}|{quarantine}".format(
                chamber=row["chamber"],
                volume=fmt2(row["accepted_volume_ml"]),
                accepted=row["accepted_count"],
                deferred=row["deferred_count"],
                quarantine=row["quarantine_count"],
            )
        )
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    """Write a CSV fixture with a fixed header."""
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def write_dynamic_fixture(base: Path) -> None:
    """Create a fixture with sparse ranks, transfer carryover, and waiver exhaustion."""
    base.mkdir(parents=True, exist_ok=True)
    (base / "policy.json").write_text(
        json.dumps(
            {
                "schema_version": "karst.dripline.policy.v1",
                "output_schema_version": "karst.dripline.audit.v1",
                "chamber_rank": {"delta": 5, "alpha": 0},
                "thresholds": {
                    "ec_min": "100",
                    "ec_max": "450",
                    "turbidity_max": "5",
                    "delta_o18_min": "-10",
                    "delta_o18_max": "-6",
                },
            },
            indent=2,
        )
    )
    write_csv(
        base / "sensors.csv",
        ["sensor_id", "chamber", "station_id", "status", "installed_at"],
        [
            ["A-1", "alpha", "A", "active", "2026-01-01T00:00:00Z"],
            ["D-1", "delta", "D", "maintenance", "2026-01-01T00:00:00Z"],
            ["Z-1", "zeta", "Z", "active", "2026-01-01T00:00:00Z"],
        ],
    )
    write_csv(
        base / "batches.csv",
        ["batch_id", "chamber", "window_start", "window_end", "capacity_ml"],
        [
            ["BX", "alpha", "2026-02-28T00:00:00Z", "2026-02-28T01:00:00Z", "30"],
            ["BA", "alpha", "2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z", "50"],
            ["BD", "delta", "2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z", "30"],
            ["BZ", "zeta", "2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z", "20"],
        ],
    )
    write_csv(
        base / "waivers.csv",
        ["waiver_id", "batch_id", "sensor_id", "kind", "expires_at", "capacity_bonus_ml"],
        [
            ["W-D-M", "BD", "D-1", "maintenance_override", "2026-03-01T23:00:00Z", "0"],
            ["W-D-B", "BD", "D-1", "capacity_bonus", "2026-03-01T23:00:00Z", "10"],
            ["W-Z-X", "BZ", "*", "capacity_bonus", "2026-02-28T23:00:00Z", "50"],
        ],
    )
    write_csv(
        base / "transfers.csv",
        [
            "transfer_id",
            "source_batch_id",
            "target_batch_id",
            "opens_at",
            "expires_at",
            "max_transfer_ml",
            "efficiency_ppm",
        ],
        [
            ["T-XA", "BX", "BA", "2026-02-28T00:00:00Z", "2026-03-01T23:00:00Z", "20", "1000000"],
            ["T-BAZ", "BA", "BZ", "2026-03-01T00:00:00Z", "2026-03-02T00:00:00Z", "15", "500000"],
        ],
    )
    rows = [
        {
            "obs_id": "A-first",
            "sensor_id": "A-1",
            "batch_id": "BA",
            "captured_at": "2026-03-01T01:00:00Z",
            "volume_ml": "45",
            "ec_uS_cm": "200",
            "delta_o18": "-8",
            "turbidity_ntu": "2",
            "operator": "nira",
        },
        {
            "obs_id": "D-critical",
            "sensor_id": "D-1",
            "batch_id": "BD",
            "captured_at": "2026-03-01T01:10:00Z",
            "volume_ml": "40",
            "ec_uS_cm": "600",
            "delta_o18": "-5",
            "turbidity_ntu": "9",
            "operator": "nira",
        },
        {
            "obs_id": "A-second",
            "sensor_id": "A-1",
            "batch_id": "BA",
            "captured_at": "2026-03-01T01:30:00Z",
            "volume_ml": "20",
            "ec_uS_cm": "210",
            "delta_o18": "-8",
            "turbidity_ntu": "2",
            "operator": "nira",
        },
        {
            "obs_id": "Z-last",
            "sensor_id": "Z-1",
            "batch_id": "BZ",
            "captured_at": "2026-03-01T01:05:00Z",
            "volume_ml": "25",
            "ec_uS_cm": "210",
            "delta_o18": "-8",
            "turbidity_ntu": "2",
            "operator": "nira",
        },
    ]
    (base / "observations.ndjson").write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_public_fixture_exercises_stateful_transfer_allocation_and_schema(tmp_path: Path) -> None:
    """Verify the bundled input exercises transfers, waivers, summaries, and schema order."""
    out = tmp_path / "nested" / "dripline_report.json"
    proc = run_cli(APP_DIR / "input", out)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""
    report = load_report(out)

    assert list(report.keys()) == [
        "schema_version",
        "allocation_order",
        "accepted_observations",
        "deferred_observations",
        "quarantine",
        "batch_summary",
        "transfer_summary",
        "chamber_summary",
        "digest",
    ]
    assert report["schema_version"] == "karst.dripline.audit.v1"
    assert report["allocation_order"] == ["O-101", "O-100", "O-102", "O-200", "O-201"]
    accepted = {row["obs_id"]: row for row in report["accepted_observations"]}
    assert list(accepted) == ["O-101", "O-100", "O-200", "O-201"]
    assert accepted["O-101"]["reason_codes"] == [
        "maintenance_waived",
        "ec_out_of_range",
        "turbidity_high",
        "isotope_shift",
    ]
    assert accepted["O-100"]["capacity_source"] == "base+bonus"
    assert accepted["O-201"]["reason_codes"] == ["transfer_capacity"]
    assert accepted["O-201"]["capacity_source"] == "base+transfer"
    assert report["deferred_observations"] == [
        {
            "obs_id": "O-102",
            "batch_id": "B-A",
            "chamber": "rimstone",
            "requested_ml": 100,
            "remaining_base_ml": 0,
            "available_transfer_ml": 0,
            "available_bonus_ml": 20,
            "reason_codes": ["capacity_exhausted"],
            "sequence_index": 3,
        }
    ]
    assert [row["code"] for row in report["quarantine"]] == [
        "outside_batch_window",
        "unknown_sensor",
        "duplicate_obs_id",
        "bad_numeric",
    ]
    b_b = next(row for row in report["batch_summary"] if row["batch_id"] == "B-B")
    assert b_b["transfer_in_ml"] == 15
    assert b_b["transfer_used_ml"] == 15
    assert b_b["bonus_used_ml"] == 0
    assert b_b["risk_counts"] == {"normal": 1, "watch": 1, "critical": 0}
    assert report["transfer_summary"] == [
        {
            "transfer_id": "T-01",
            "source_batch_id": "B-C",
            "target_batch_id": "B-B",
            "requested_ml": 30,
            "transferred_ml": 15,
            "consumed_ml": 15,
            "status": "materialized",
        },
        {
            "transfer_id": "T-02",
            "source_batch_id": "B-A",
            "target_batch_id": "B-B",
            "requested_ml": 25,
            "transferred_ml": 0,
            "consumed_ml": 0,
            "status": "inactive_window",
        },
        {
            "transfer_id": "T-03",
            "source_batch_id": "B-A",
            "target_batch_id": "B-C",
            "requested_ml": 50,
            "transferred_ml": 0,
            "consumed_ml": 0,
            "status": "no_source_capacity",
        },
    ]
    chamber = {row["chamber"]: row for row in report["chamber_summary"]}
    assert chamber["rimstone"] == {
        "chamber": "rimstone",
        "accepted_volume_ml": 135,
        "accepted_count": 2,
        "deferred_count": 1,
        "quarantine_count": 3,
    }
    assert chamber["moonmilk"]["accepted_volume_ml"] == 75
    assert chamber["soda-straw"]["quarantine_count"] == 1


def test_dynamic_fixture_uses_sparse_rank_transfer_and_waiver_ledgers(tmp_path: Path) -> None:
    """Verify sparse ranks, no-candidate source transfers, and bonus ledgers interact."""
    fixture = tmp_path / "fixture"
    write_dynamic_fixture(fixture)
    out = tmp_path / "out" / "report.json"
    proc = run_cli(fixture, out)
    assert proc.returncode == 0, proc.stderr
    report = load_report(out)

    assert report["allocation_order"] == ["A-first", "A-second", "D-critical", "Z-last"]
    accepted = {row["obs_id"]: row for row in report["accepted_observations"]}
    deferred = {row["obs_id"]: row for row in report["deferred_observations"]}
    assert accepted["A-second"]["reason_codes"] == ["transfer_capacity"]
    assert accepted["A-second"]["capacity_source"] == "base+transfer"
    assert accepted["D-critical"]["reason_codes"] == [
        "maintenance_waived",
        "ec_out_of_range",
        "turbidity_high",
        "isotope_shift",
        "capacity_waived",
    ]
    assert accepted["D-critical"]["capacity_source"] == "base+bonus"
    assert deferred["Z-last"]["remaining_base_ml"] == 20
    assert deferred["Z-last"]["available_transfer_ml"] == 0
    assert deferred["Z-last"]["available_bonus_ml"] == 0
    transfers = {row["transfer_id"]: row for row in report["transfer_summary"]}
    assert transfers["T-XA"]["transferred_ml"] == 20
    assert transfers["T-XA"]["consumed_ml"] == 15
    assert transfers["T-BAZ"]["status"] == "no_source_capacity"
    batch_alpha = next(row for row in report["batch_summary"] if row["batch_id"] == "BA")
    assert batch_alpha["transfer_in_ml"] == 20
    assert batch_alpha["transfer_used_ml"] == 15
    assert [row["chamber"] for row in report["chamber_summary"]] == ["alpha", "delta", "zeta"]


def test_dynamic_validation_short_circuit_numeric_grammar_and_unknown_chamber(tmp_path: Path) -> None:
    """Verify every observation validation branch and first-failure ordering."""
    fixture = tmp_path / "fixture"
    write_dynamic_fixture(fixture)
    lines = [
        "{not-json",
        json.dumps(
            {
                "obs_id": "",
                "sensor_id": "A-1",
                "batch_id": "BA",
                "captured_at": "2026-03-01T01:00:00Z",
                "volume_ml": "9",
                "ec_uS_cm": "200",
                "delta_o18": "-8",
                "turbidity_ntu": "2",
                "operator": "nira",
            }
        ),
        json.dumps(
            {
                "obs_id": "DUP-1",
                "sensor_id": "A-1",
                "batch_id": "BA",
                "captured_at": "2026-03-01T01:05:00Z",
                "volume_ml": "9",
                "ec_uS_cm": "200",
                "delta_o18": "-8",
                "turbidity_ntu": "2",
                "operator": "nira",
            }
        ),
        json.dumps(
            {
                "obs_id": "DUP-1",
                "sensor_id": "NOPE",
                "batch_id": "NOPE",
                "captured_at": "2026-03-01T01:06:00Z",
                "volume_ml": "+9",
                "ec_uS_cm": "200",
                "delta_o18": "-8",
                "turbidity_ntu": "2",
                "operator": "nira",
            }
        ),
        json.dumps(
            {
                "obs_id": "BAD-SENSOR",
                "sensor_id": "NOPE",
                "batch_id": "NOPE",
                "captured_at": "2026-03-01T01:10:00Z",
                "volume_ml": "+9",
                "ec_uS_cm": "200",
                "delta_o18": "-8",
                "turbidity_ntu": "2",
                "operator": "nira",
            }
        ),
        json.dumps(
            {
                "obs_id": "BAD-BATCH",
                "sensor_id": "A-1",
                "batch_id": "NOPE",
                "captured_at": "2026-03-01T01:15:00Z",
                "volume_ml": "9",
                "ec_uS_cm": "200",
                "delta_o18": "-8",
                "turbidity_ntu": "2",
                "operator": "nira",
            }
        ),
        json.dumps(
            {
                "obs_id": "BAD-CHAMBER",
                "sensor_id": "A-1",
                "batch_id": "BD",
                "captured_at": "2026-03-01T01:20:00Z",
                "volume_ml": "9",
                "ec_uS_cm": "200",
                "delta_o18": "-8",
                "turbidity_ntu": "2",
                "operator": "nira",
            }
        ),
        json.dumps(
            {
                "obs_id": "BAD-TIME",
                "sensor_id": "A-1",
                "batch_id": "BA",
                "captured_at": "not-a-time",
                "volume_ml": "9",
                "ec_uS_cm": "200",
                "delta_o18": "-8",
                "turbidity_ntu": "2",
                "operator": "nira",
            }
        ),
        json.dumps(
            {
                "obs_id": "BAD-WINDOW",
                "sensor_id": "A-1",
                "batch_id": "BA",
                "captured_at": "2026-03-02T00:00:00Z",
                "volume_ml": "9",
                "ec_uS_cm": "200",
                "delta_o18": "-8",
                "turbidity_ntu": "2",
                "operator": "nira",
            }
        ),
        json.dumps(
            {
                "obs_id": "BAD-STATUS",
                "sensor_id": "D-1",
                "batch_id": "BD",
                "captured_at": "2026-03-01T23:30:00Z",
                "volume_ml": "9",
                "ec_uS_cm": "200",
                "delta_o18": "-8",
                "turbidity_ntu": "2",
                "operator": "nira",
            }
        ),
        json.dumps(
            {
                "obs_id": "BAD-NUMERIC",
                "sensor_id": "A-1",
                "batch_id": "BA",
                "captured_at": "2026-03-01T01:25:00Z",
                "volume_ml": "+9",
                "ec_uS_cm": "200",
                "delta_o18": "-8",
                "turbidity_ntu": "2",
                "operator": "nira",
            }
        ),
        json.dumps(
            {
                "obs_id": "BAD-ZERO",
                "sensor_id": "A-1",
                "batch_id": "BA",
                "captured_at": "2026-03-01T01:30:00Z",
                "volume_ml": "0",
                "ec_uS_cm": "200",
                "delta_o18": "-8",
                "turbidity_ntu": "2",
                "operator": "nira",
            }
        ),
    ]
    (fixture / "observations.ndjson").write_text("\n".join(lines) + "\n")
    out = tmp_path / "report.json"
    proc = run_cli(fixture, out)
    assert proc.returncode == 0, proc.stderr
    report = load_report(out)

    assert report["allocation_order"] == ["DUP-1"]
    assert [row["code"] for row in report["quarantine"]] == [
        "bad_json",
        "missing_obs_id",
        "duplicate_obs_id",
        "unknown_sensor",
        "unknown_batch",
        "chamber_mismatch",
        "bad_timestamp",
        "outside_batch_window",
        "sensor_not_active",
        "bad_numeric",
        "nonpositive_volume",
    ]
    assert [row["record_id"] for row in report["quarantine"]] == [
        f"line:{line_no}" for line_no in range(1, 13) if line_no != 3
    ]
    assert [row["detail"] for row in report["quarantine"]] == [
        "line:1|json",
        "obs_id missing",
        "obs_id:DUP-1",
        "sensor:NOPE",
        "batch:NOPE",
        "sensor:alpha|batch:delta",
        "captured_at:not-a-time",
        "batch:BA",
        "sensor:D-1|status:maintenance",
        "volume_ml:+9",
        "volume_ml:0",
    ]
    chambers = {row["chamber"]: row for row in report["chamber_summary"]}
    assert chambers["unknown"] == {
        "chamber": "unknown",
        "accepted_volume_ml": 0,
        "accepted_count": 0,
        "deferred_count": 0,
        "quarantine_count": 3,
    }
    assert chambers["alpha"]["quarantine_count"] == 7
    assert chambers["delta"]["quarantine_count"] == 1


def test_digest_is_recomputed_from_canonical_lines(tmp_path: Path) -> None:
    """Verify digest canonicalization covers transfers and chamber summaries."""
    out = tmp_path / "report.json"
    proc = run_cli(APP_DIR / "input", out)
    assert proc.returncode == 0, proc.stderr
    report = load_report(out)
    assert report["digest"] == recompute_digest(report)
    assert len(report["digest"]) == 64
    assert report["digest"].islower()
    altered = json.loads(json.dumps(report))
    altered["transfer_summary"][0]["consumed_ml"] = 14
    assert report["digest"] != recompute_digest(altered)


def test_transfer_efficiency_source_reservation_and_statuses(tmp_path: Path) -> None:
    """Verify transfer efficiency reserves source capacity and changes target acceptance."""
    fixture = tmp_path / "fixture"
    write_dynamic_fixture(fixture)
    write_csv(
        fixture / "transfers.csv",
        [
            "transfer_id",
            "source_batch_id",
            "target_batch_id",
            "opens_at",
            "expires_at",
            "max_transfer_ml",
            "efficiency_ppm",
        ],
        [
            ["T-HALF", "BX", "BA", "2026-02-28T00:00:00Z", "2026-03-01T23:00:00Z", "20", "500000"],
            ["T-UNKNOWN", "BX", "MISSING", "2026-02-28T00:00:00Z", "2026-03-01T23:00:00Z", "5", "1000000"],
            ["T-LATE", "BA", "BZ", "2026-03-01T00:00:00Z", "2026-03-01T12:00:00Z", "10", "1000000"],
        ],
    )
    out = tmp_path / "report.json"
    proc = run_cli(fixture, out)
    assert proc.returncode == 0, proc.stderr
    report = load_report(out)
    accepted = {row["obs_id"]: row for row in report["accepted_observations"]}
    deferred = {row["obs_id"]: row for row in report["deferred_observations"]}

    assert "A-second" not in accepted
    assert deferred["A-second"]["available_transfer_ml"] == 10
    assert deferred["A-second"]["reason_codes"] == ["capacity_exhausted"]
    transfers = {row["transfer_id"]: row for row in report["transfer_summary"]}
    assert transfers["T-HALF"] == {
        "transfer_id": "T-HALF",
        "source_batch_id": "BX",
        "target_batch_id": "BA",
        "requested_ml": 20,
        "transferred_ml": 10,
        "consumed_ml": 0,
        "status": "materialized",
    }
    assert transfers["T-LATE"]["status"] == "inactive_window"
    assert transfers["T-UNKNOWN"]["status"] == "unknown_target_batch"


def test_output_path_overwrite_and_missing_parent_behavior(tmp_path: Path) -> None:
    """Verify nested output parents are created and existing files are overwritten."""
    out = tmp_path / "a" / "b" / "existing.json"
    out.parent.mkdir(parents=True)
    out.write_text("old content")
    proc = run_cli(APP_DIR / "input", out)
    assert proc.returncode == 0, proc.stderr
    assert out.exists()
    assert "old content" not in out.read_text()
    assert load_report(out)["schema_version"] == "karst.dripline.audit.v1"


def test_missing_input_directory_fails_cleanly(tmp_path: Path) -> None:
    """Verify the documented missing-input stderr contract and no output side effect."""
    missing = tmp_path / "does-not-exist"
    out = tmp_path / "out" / "report.json"
    proc = run_cli(missing, out)
    assert proc.returncode != 0
    assert "missing input directory" in proc.stderr
    assert not out.exists()


def test_oracle_does_not_require_mutating_bundled_input(tmp_path: Path) -> None:
    """Verify the CLI works on a copied input tree rather than relying on fixed paths."""
    fixture = tmp_path / "copied-input"
    shutil.copytree(APP_DIR / "input", fixture)
    out = tmp_path / "custom" / "report.json"
    proc = run_cli(fixture, out)
    assert proc.returncode == 0, proc.stderr
    report = load_report(out)
    assert report["allocation_order"][0] == "O-101"
    assert report["transfer_summary"][0]["status"] == "materialized"
    assert report["digest"] == recompute_digest(report)
