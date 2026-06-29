"""Behavioral verifier for the deployment health-window reconciler."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

APP_CMD = "/app/bin/reconcile-health-windows"
CONFIG_PATH = "/app/config/health-window-policy.json"
BUNDLED_INPUT = "/app/fixtures"

WINDOW_FIELDS = {
    "deployment_id",
    "service",
    "environment",
    "release_id",
    "owner",
    "window_start",
    "window_end",
    "duration_minutes",
    "required_probe_types",
    "observed_probe_ids",
    "missing_probe_types",
    "failed_probe_ids",
    "incident_ids",
    "depends_on",
    "freeze_window_ids",
    "policy_violation_codes",
    "base_health_state",
    "blocked_by_deployment_ids",
    "rollback_marker_id",
    "rollback_effective_at",
    "health_state",
}
WARNING_FIELDS = {"code", "severity", "subject_id", "source_path", "source_line", "detail"}


def run_reconciler(input_dir: Path | str, output_dir: Path, config_path: Path | str = CONFIG_PATH) -> tuple[dict, dict]:
    """Run the public CLI and return both generated JSON reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            APP_CMD,
            "--config",
            str(config_path),
            "--input",
            str(input_dir),
            "--out",
            str(output_dir),
        ],
        cwd="/app",
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr + result.stdout
    health_path = output_dir / "health_windows.json"
    warnings_path = output_dir / "reconciliation_warnings.json"
    assert health_path.exists(), "health_windows.json was not written"
    assert warnings_path.exists(), "reconciliation_warnings.json was not written"
    return json.loads(health_path.read_text()), json.loads(warnings_path.read_text())


def write_jsonl(path: Path, rows: list[dict | str]) -> None:
    """Write JSONL rows, preserving raw malformed strings when requested."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            if isinstance(row, str):
                handle.write(row + "\n")
            else:
                handle.write(json.dumps(row, sort_keys=True) + "\n")


def by_id(rows: list[dict]) -> dict[str, dict]:
    """Index output rows by deployment id."""
    return {row["deployment_id"]: row for row in rows}


def test_bundled_fixture_reconciles_cross_feed_health_windows(tmp_path: Path) -> None:
    """The bundled feeds produce deterministic health windows with rollback suppression and evidence preserved."""
    health, warnings = run_reconciler(BUNDLED_INPUT, tmp_path / "out")

    assert health["generated_by"] == "go-deployment-health-window-reconciler"
    assert health["summary"] == {
        "deployments_total": 4,
        "windows_total": 4,
        "healthy_count": 0,
        "degraded_count": 0,
        "failed_count": 0,
        "rolled_back_count": 1,
        "blocked_count": 2,
        "frozen_count": 1,
        "policy_violation_count": 3,
        "warnings_total": len(warnings["warnings"]),
    }
    assert [window["deployment_id"] for window in health["windows"]] == ["dep-100", "dep-400", "dep-300", "dep-200"]
    assert all(set(window) == WINDOW_FIELDS for window in health["windows"])

    windows = by_id(health["windows"])
    assert windows["dep-100"]["environment"] == "production"
    assert windows["dep-100"]["window_start"] == "2026-06-01T10:00:00Z"
    assert windows["dep-100"]["window_end"] == "2026-06-01T10:45:00Z"
    assert windows["dep-100"]["required_probe_types"] == ["http", "readiness", "synthetic"]
    assert windows["dep-100"]["observed_probe_ids"] == ["p-http-100", "p-ready-100", "p-synth-100"]
    assert windows["dep-100"]["missing_probe_types"] == ["synthetic"]
    assert windows["dep-100"]["failed_probe_ids"] == ["p-synth-100"]
    assert windows["dep-100"]["incident_ids"] == ["inc-100"]
    assert windows["dep-100"]["depends_on"] == []
    assert windows["dep-100"]["freeze_window_ids"] == ["freeze-prod-api"]
    assert windows["dep-100"]["policy_violation_codes"] == ["hard_freeze_overlap", "rollback_during_freeze"]
    assert windows["dep-100"]["base_health_state"] == "rolled_back"
    assert windows["dep-100"]["blocked_by_deployment_ids"] == []
    assert windows["dep-100"]["rollback_marker_id"] == "rb-100"
    assert windows["dep-100"]["rollback_effective_at"] == "2026-06-01T10:35:00Z"
    assert windows["dep-100"]["health_state"] == "rolled_back"

    assert windows["dep-400"]["environment"] == "production"
    assert windows["dep-400"]["required_probe_types"] == ["http", "readiness"]
    assert windows["dep-400"]["observed_probe_ids"] == ["p-http-400", "p-ready-400"]
    assert windows["dep-400"]["missing_probe_types"] == []
    assert windows["dep-400"]["failed_probe_ids"] == []
    assert windows["dep-400"]["freeze_window_ids"] == ["freeze-prod-frontend"]
    assert windows["dep-400"]["policy_violation_codes"] == ["hard_freeze_overlap"]
    assert windows["dep-400"]["base_health_state"] == "healthy"
    assert windows["dep-400"]["health_state"] == "frozen"

    assert windows["dep-300"]["observed_probe_ids"] == ["p-http-300"]
    assert windows["dep-300"]["missing_probe_types"] == ["readiness", "synthetic"]
    assert windows["dep-300"]["incident_ids"] == []
    assert windows["dep-300"]["depends_on"] == ["dep-100", "dep-missing"]
    assert windows["dep-300"]["freeze_window_ids"] == []
    assert windows["dep-300"]["policy_violation_codes"] == []
    assert windows["dep-300"]["base_health_state"] == "degraded"
    assert windows["dep-300"]["blocked_by_deployment_ids"] == ["dep-100"]
    assert windows["dep-300"]["health_state"] == "blocked"

    assert windows["dep-200"]["environment"] == "staging"
    assert windows["dep-200"]["observed_probe_ids"] == ["p-http-200", "p-ready-200"]
    assert windows["dep-200"]["incident_ids"] == ["inc-200"]
    assert windows["dep-200"]["depends_on"] == ["dep-300"]
    assert windows["dep-200"]["freeze_window_ids"] == ["freeze-stage-billing"]
    assert windows["dep-200"]["policy_violation_codes"] == []
    assert windows["dep-200"]["base_health_state"] == "degraded"
    assert windows["dep-200"]["blocked_by_deployment_ids"] == ["dep-300"]
    assert windows["dep-200"]["health_state"] == "blocked"


def test_bundled_fixture_emits_documented_warning_shapes_and_sorting(tmp_path: Path) -> None:
    """Bundled malformed, duplicate, unknown, mismatch, and late-marker cases use documented warnings."""
    _, warnings_report = run_reconciler(BUNDLED_INPUT, tmp_path / "out")
    warnings = warnings_report["warnings"]

    assert warnings_report["generated_by"] == "go-deployment-health-window-reconciler"
    assert len(warnings) == 10
    assert all(set(warning) == WARNING_FIELDS for warning in warnings)
    assert warnings == sorted(
        warnings,
        key=lambda item: (
            item["code"],
            item["subject_id"],
            item["source_path"],
            item["source_line"],
            item["detail"],
        ),
    )

    by_code_subject = {(warning["code"], warning["subject_id"]): warning for warning in warnings}
    assert by_code_subject[("duplicate_deployment", "dep-100")] == {
        "code": "duplicate_deployment",
        "severity": "warning",
        "subject_id": "dep-100",
        "source_path": "shadow/duplicate_deployments.jsonl",
        "source_line": 1,
        "detail": "duplicate deployment dep-100; kept regions/us/deployments.jsonl:1",
    }
    assert by_code_subject[("invalid_deployment", "dep-invalid")]["detail"] == (
        "invalid deployment dep-invalid: missing required field service"
    )
    assert by_code_subject[("invalid_freeze", "freeze-invalid")] == {
        "code": "invalid_freeze",
        "severity": "error",
        "subject_id": "freeze-invalid",
        "source_path": "regions/us/freezes.jsonl",
        "source_line": 4,
        "detail": "invalid freeze freeze-invalid: missing required field ends_at",
    }
    assert by_code_subject[("malformed_json", "")]["source_line"] == 3
    assert by_code_subject[("probe_service_mismatch", "p-mismatch-300")]["detail"] == (
        "probe p-mismatch-300 targets worker/staging but deployment dep-300 is worker/production"
    )
    assert by_code_subject[("late_rollback", "rb-late-200")]["detail"] == (
        "rollback rb-late-200 marked after grace window for deployment dep-200"
    )
    assert ("unknown_probe_deployment", "p-ghost") in by_code_subject
    assert ("unknown_incident_deployment", "inc-ghost") in by_code_subject
    assert ("unknown_rollback_deployment", "rb-ghost") in by_code_subject
    assert by_code_subject[("unknown_dependency", "dep-300")] == {
        "code": "unknown_dependency",
        "severity": "warning",
        "subject_id": "dep-300",
        "source_path": "regions/eu/deployments.jsonl",
        "source_line": 1,
        "detail": "deployment dep-300 depends on unknown deployment dep-missing",
    }


def test_rerun_cleans_stale_json_without_removing_unrelated_files(tmp_path: Path) -> None:
    """Rerunning replaces the two report files and removes stale JSON while preserving non-JSON files."""
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    stale_json = out_dir / "old_report.json"
    keep_file = out_dir / "operator-note.txt"
    stale_json.write_text('{"stale": true}\n', encoding="utf-8")
    keep_file.write_text("do not remove\n", encoding="utf-8")

    first_health, first_warnings = run_reconciler(BUNDLED_INPUT, out_dir)
    assert not stale_json.exists()
    assert keep_file.read_text(encoding="utf-8") == "do not remove\n"

    second_health, second_warnings = run_reconciler(BUNDLED_INPUT, out_dir)
    assert second_health == first_health
    assert second_warnings == first_warnings
    assert sorted(path.name for path in out_dir.glob("*.json")) == [
        "health_windows.json",
        "reconciliation_warnings.json",
    ]


def test_dynamic_fixture_exercises_window_boundaries_and_rollback_suppression(tmp_path: Path) -> None:
    """A generated feed verifies inclusive probe/incident/rollback boundaries and evidence-preserving rollback state."""
    feed = tmp_path / "feed"
    write_jsonl(
        feed / "deployments.jsonl",
        [
            {
                "deployment_id": "dyn-rollback",
                "service": "checkout",
                "environment": "prod",
                "started_at": "2026-06-02T00:00:00Z",
                "duration_minutes": 10,
                "required_probes": ["http"],
                "priority": 1,
            }
        ],
    )
    write_jsonl(
        feed / "probes.jsonl",
        [
            {
                "probe_id": "edge-fail",
                "deployment_id": "dyn-rollback",
                "service": "checkout",
                "environment": "production",
                "probe_type": "http-check",
                "checked_at": "2026-06-02T00:10:00Z",
                "status": "error",
            }
        ],
    )
    write_jsonl(
        feed / "incidents.jsonl",
        [
            {
                "incident_id": "edge-critical",
                "deployment_id": "dyn-rollback",
                "started_at": "2026-06-02T00:10:00Z",
                "severity": "sev1",
            }
        ],
    )
    write_jsonl(
        feed / "rollbacks.jsonl",
        [
            {
                "rollback_id": "edge-rollback",
                "deployment_id": "dyn-rollback",
                "marked_at": "2026-06-02T00:25:00Z",
                "state": "complete",
            }
        ],
    )

    health, warnings = run_reconciler(feed, tmp_path / "out")
    assert warnings["warnings"] == []
    window = health["windows"][0]
    assert window["window_end"] == "2026-06-02T00:10:00Z"
    assert window["observed_probe_ids"] == ["edge-fail"]
    assert window["failed_probe_ids"] == ["edge-fail"]
    assert window["missing_probe_types"] == ["http"]
    assert window["incident_ids"] == ["edge-critical"]
    assert window["base_health_state"] == "rolled_back"
    assert window["blocked_by_deployment_ids"] == []
    assert window["rollback_marker_id"] == "edge-rollback"
    assert window["rollback_effective_at"] == "2026-06-02T00:25:00Z"
    assert window["health_state"] == "rolled_back"


def test_dynamic_duplicate_tie_break_uses_source_path_and_reports_discarded_row(tmp_path: Path) -> None:
    """When priority and timestamp tie, the lexicographically smallest source path wins and the loser is warned."""
    feed = tmp_path / "feed"
    shared = {
        "deployment_id": "tie-dep",
        "environment": "prod",
        "started_at": "2026-06-03T12:00:00Z",
        "duration_minutes": 5,
        "required_probes": ["http"],
        "priority": 7,
    }
    write_jsonl(feed / "a" / "deployments.jsonl", [shared | {"service": "alpha", "owner": "winner"}])
    write_jsonl(feed / "b" / "deployments.jsonl", [shared | {"service": "beta", "owner": "loser"}])
    write_jsonl(
        feed / "a" / "probes.jsonl",
        [
            {
                "probe_id": "tie-pass",
                "deployment_id": "tie-dep",
                "service": "alpha",
                "environment": "prd",
                "probe_type": "http",
                "checked_at": "2026-06-03T12:03:00Z",
                "status": "healthy",
            }
        ],
    )

    health, warnings_report = run_reconciler(feed, tmp_path / "out")
    assert len(health["windows"]) == 1
    window = health["windows"][0]
    assert window["service"] == "alpha"
    assert window["owner"] == "winner"
    assert window["depends_on"] == []
    assert window["base_health_state"] == "healthy"
    assert window["blocked_by_deployment_ids"] == []
    assert window["observed_probe_ids"] == ["tie-pass"]
    assert window["health_state"] == "healthy"

    warnings = warnings_report["warnings"]
    assert warnings == [
        {
            "code": "duplicate_deployment",
            "severity": "warning",
            "subject_id": "tie-dep",
            "source_path": "b/deployments.jsonl",
            "source_line": 1,
            "detail": "duplicate deployment tie-dep; kept a/deployments.jsonl:1",
        }
    ]


def test_dynamic_unknown_parents_short_circuit_late_and_mismatch_checks(tmp_path: Path) -> None:
    """Unknown parent ids emit only their unknown warnings and do not trigger late rollback or mismatch side effects."""
    feed = tmp_path / "feed"
    write_jsonl(
        feed / "deployments.jsonl",
        [
            {
                "deployment_id": "known",
                "service": "api",
                "environment": "prod",
                "started_at": "2026-06-04T09:00:00Z",
                "duration_minutes": 5,
                "required_probes": ["http"],
            }
        ],
    )
    write_jsonl(
        feed / "probes.jsonl",
        [
            {
                "probe_id": "unknown-probe",
                "deployment_id": "missing",
                "service": "wrong",
                "environment": "stage",
                "probe_type": "http",
                "checked_at": "2026-06-04T09:01:00Z",
                "status": "ok",
            }
        ],
    )
    write_jsonl(
        feed / "incidents.jsonl",
        [
            {
                "incident_id": "unknown-incident",
                "deployment_id": "missing",
                "started_at": "2026-06-04T09:01:00Z",
                "severity": "critical",
            }
        ],
    )
    write_jsonl(
        feed / "rollbacks.jsonl",
        [
            {
                "rollback_id": "unknown-rollback",
                "deployment_id": "missing",
                "marked_at": "2026-06-04T10:00:00Z",
                "state": "applied",
            }
        ],
    )

    health, warnings_report = run_reconciler(feed, tmp_path / "out")
    assert health["windows"][0]["base_health_state"] == "degraded"
    assert health["windows"][0]["health_state"] == "degraded"
    assert health["windows"][0]["blocked_by_deployment_ids"] == []
    warnings = warnings_report["warnings"]
    assert [warning["code"] for warning in warnings] == [
        "unknown_incident_deployment",
        "unknown_probe_deployment",
        "unknown_rollback_deployment",
    ]
    assert "probe_service_mismatch" not in {warning["code"] for warning in warnings}
    assert "late_rollback" not in {warning["code"] for warning in warnings}


def test_dynamic_dependency_blocking_cycles_and_unknown_dependencies(tmp_path: Path) -> None:
    """Generated dependencies verify transitive blocking, unknown dependency warnings, and cycle suppression."""
    feed = tmp_path / "feed"
    deployments = [
        {
            "deployment_id": "root-fail",
            "service": "api",
            "environment": "prod",
            "started_at": "2026-06-05T00:00:00Z",
            "duration_minutes": 10,
            "required_probes": ["http"],
        },
        {
            "deployment_id": "middle",
            "service": "api",
            "environment": "prod",
            "started_at": "2026-06-05T00:20:00Z",
            "duration_minutes": 10,
            "required_probes": ["http"],
            "depends_on": ["root-fail"],
        },
        {
            "deployment_id": "leaf",
            "service": "api",
            "environment": "prod",
            "started_at": "2026-06-05T00:40:00Z",
            "duration_minutes": 10,
            "required_probes": ["http"],
            "depends_on": ["middle"],
        },
        {
            "deployment_id": "cycle-a",
            "service": "jobs",
            "environment": "stage",
            "started_at": "2026-06-05T01:00:00Z",
            "duration_minutes": 10,
            "required_probes": ["http"],
            "depends_on": ["cycle-b"],
        },
        {
            "deployment_id": "cycle-b",
            "service": "jobs",
            "environment": "stage",
            "started_at": "2026-06-05T01:20:00Z",
            "duration_minutes": 10,
            "required_probes": ["http"],
            "depends_on": ["cycle-a"],
        },
        {
            "deployment_id": "unknown-dep",
            "service": "web",
            "environment": "prod",
            "started_at": "2026-06-05T02:00:00Z",
            "duration_minutes": 10,
            "required_probes": ["http"],
            "depends_on": ["missing-root"],
        },
    ]
    write_jsonl(feed / "deployments.jsonl", deployments)
    write_jsonl(
        feed / "probes.jsonl",
        [
            {
                "probe_id": "root-fail-probe",
                "deployment_id": "root-fail",
                "service": "api",
                "environment": "production",
                "probe_type": "http",
                "checked_at": "2026-06-05T00:03:00Z",
                "status": "failed",
            },
            *[
                {
                    "probe_id": f"{deployment_id}-pass",
                    "deployment_id": deployment_id,
                    "service": service,
                    "environment": environment,
                    "probe_type": "http-check",
                    "checked_at": checked_at,
                    "status": "ok",
                }
                for deployment_id, service, environment, checked_at in [
                    ("middle", "api", "production", "2026-06-05T00:25:00Z"),
                    ("leaf", "api", "production", "2026-06-05T00:45:00Z"),
                    ("cycle-a", "jobs", "staging", "2026-06-05T01:03:00Z"),
                    ("cycle-b", "jobs", "staging", "2026-06-05T01:23:00Z"),
                    ("unknown-dep", "web", "production", "2026-06-05T02:03:00Z"),
                ]
            ],
        ],
    )

    health, warnings_report = run_reconciler(feed, tmp_path / "out")
    windows = by_id(health["windows"])
    assert windows["root-fail"]["base_health_state"] == "failed"
    assert windows["root-fail"]["health_state"] == "failed"
    assert windows["middle"]["base_health_state"] == "healthy"
    assert windows["middle"]["health_state"] == "blocked"
    assert windows["middle"]["blocked_by_deployment_ids"] == ["root-fail"]
    assert windows["leaf"]["base_health_state"] == "healthy"
    assert windows["leaf"]["health_state"] == "blocked"
    assert windows["leaf"]["blocked_by_deployment_ids"] == ["middle"]
    assert windows["cycle-a"]["health_state"] == "healthy"
    assert windows["cycle-a"]["blocked_by_deployment_ids"] == []
    assert windows["cycle-b"]["health_state"] == "healthy"
    assert windows["unknown-dep"]["health_state"] == "healthy"

    codes_and_subjects = {(warning["code"], warning["subject_id"]): warning for warning in warnings_report["warnings"]}
    assert codes_and_subjects[("dependency_cycle", "cycle-a")]["detail"] == (
        "deployment cycle-a participates in dependency cycle cycle-a,cycle-b"
    )
    assert codes_and_subjects[("dependency_cycle", "cycle-b")]["detail"] == (
        "deployment cycle-b participates in dependency cycle cycle-a,cycle-b"
    )
    assert codes_and_subjects[("unknown_dependency", "unknown-dep")]["detail"] == (
        "deployment unknown-dep depends on unknown deployment missing-root"
    )
    assert health["summary"]["blocked_count"] == 2



def test_dynamic_change_freeze_policy_interacts_with_rollbacks_dependencies_and_owner_exemptions(tmp_path: Path) -> None:
    """Generated freeze feeds verify scoped overlaps, owner exemptions, rollback policy codes, and state priority."""
    feed = tmp_path / "feed"
    write_jsonl(
        feed / "deployments.jsonl",
        [
            {
                "deployment_id": "frozen-ok",
                "service": "api",
                "environment": "prod",
                "owner": "team-a",
                "started_at": "2026-06-06T00:00:00Z",
                "duration_minutes": 20,
                "required_probes": ["http"],
            },
            {
                "deployment_id": "rollback-freeze",
                "service": "api",
                "environment": "prod",
                "owner": "team-b",
                "started_at": "2026-06-06T01:00:00Z",
                "duration_minutes": 20,
                "required_probes": ["http"],
            },
            {
                "deployment_id": "allowed-owner",
                "service": "api",
                "environment": "prod",
                "owner": "sre",
                "started_at": "2026-06-06T02:00:00Z",
                "duration_minutes": 20,
                "required_probes": ["http"],
            },
            {
                "deployment_id": "blocked-first",
                "service": "web",
                "environment": "prod",
                "owner": "team-c",
                "started_at": "2026-06-06T03:00:00Z",
                "duration_minutes": 20,
                "required_probes": ["http"],
                "depends_on": ["rollback-freeze"],
            },
        ],
    )
    probe_rows = []
    for dep_id, service, checked_at in [
        ("frozen-ok", "api", "2026-06-06T00:05:00Z"),
        ("rollback-freeze", "api", "2026-06-06T01:05:00Z"),
        ("allowed-owner", "api", "2026-06-06T02:05:00Z"),
        ("blocked-first", "web", "2026-06-06T03:05:00Z"),
    ]:
        probe_rows.append(
            {
                "probe_id": f"{dep_id}-probe",
                "deployment_id": dep_id,
                "service": service,
                "environment": "production",
                "probe_type": "http",
                "checked_at": checked_at,
                "status": "ok",
            }
        )
    write_jsonl(feed / "probes.jsonl", probe_rows)
    write_jsonl(
        feed / "rollbacks.jsonl",
        [
            {
                "rollback_id": "rb-freeze",
                "deployment_id": "rollback-freeze",
                "marked_at": "2026-06-06T01:10:00Z",
                "state": "applied",
            }
        ],
    )
    write_jsonl(
        feed / "freezes.jsonl",
        [
            {
                "freeze_id": "freeze-hard-api",
                "environment": "prd",
                "service": "api",
                "starts_at": "2026-06-06T00:00:00Z",
                "ends_at": "2026-06-06T01:15:00Z",
                "severity": "hard",
                "allowed_owners": ["sre"],
            },
            {
                "freeze_id": "freeze-advisory-all",
                "environment": "production",
                "starts_at": "2026-06-06T02:00:00Z",
                "ends_at": "2026-06-06T03:30:00Z",
                "severity": "advisory",
            },
            {
                "freeze_id": "bad-freeze",
                "environment": "prod",
                "starts_at": "2026-06-06T04:00:00Z",
                "ends_at": "2026-06-06T03:00:00Z",
                "severity": "hard",
            },
        ],
    )

    health, warnings_report = run_reconciler(feed, tmp_path / "out")
    windows = by_id(health["windows"])
    assert windows["frozen-ok"]["base_health_state"] == "healthy"
    assert windows["frozen-ok"]["freeze_window_ids"] == ["freeze-hard-api"]
    assert windows["frozen-ok"]["policy_violation_codes"] == ["hard_freeze_overlap"]
    assert windows["frozen-ok"]["health_state"] == "frozen"

    assert windows["rollback-freeze"]["base_health_state"] == "rolled_back"
    assert windows["rollback-freeze"]["freeze_window_ids"] == ["freeze-hard-api"]
    assert windows["rollback-freeze"]["policy_violation_codes"] == [
        "hard_freeze_overlap",
        "rollback_during_freeze",
    ]
    assert windows["rollback-freeze"]["health_state"] == "rolled_back"

    assert windows["allowed-owner"]["freeze_window_ids"] == ["freeze-advisory-all"]
    assert windows["allowed-owner"]["policy_violation_codes"] == []
    assert windows["allowed-owner"]["health_state"] == "healthy"

    assert windows["blocked-first"]["freeze_window_ids"] == ["freeze-advisory-all"]
    assert windows["blocked-first"]["policy_violation_codes"] == []
    assert windows["blocked-first"]["blocked_by_deployment_ids"] == ["rollback-freeze"]
    assert windows["blocked-first"]["health_state"] == "blocked"
    assert health["summary"]["frozen_count"] == 1
    assert health["summary"]["policy_violation_count"] == 3

    assert warnings_report["warnings"] == [
        {
            "code": "invalid_freeze",
            "severity": "error",
            "subject_id": "bad-freeze",
            "source_path": "freezes.jsonl",
            "source_line": 3,
            "detail": "invalid freeze bad-freeze: ends_at before starts_at",
        }
    ]
