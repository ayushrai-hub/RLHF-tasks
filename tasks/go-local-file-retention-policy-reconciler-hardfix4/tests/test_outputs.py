"""Behavioral tests for the local file retention policy reconciler."""
import json
import subprocess
from pathlib import Path

APP = Path("/app")
CLI = ["/usr/local/go/bin/go", "run", "/app/bin/local-retention-reconciler.go"]
REQUIRED_JSON = {"retention_report.json", "cleanup_plan.json", "warnings.json"}


def run_cli(config="/app/config/retention-policy.json", manifests="/app/manifests", out="/app/out"):
    result = subprocess.run(
        [*CLI, "--config", str(config), "--manifests", str(manifests), "--out", str(out)],
        cwd=APP,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    out_path = Path(out)
    return (
        json.loads((out_path / "retention_report.json").read_text(encoding="utf-8")),
        json.loads((out_path / "cleanup_plan.json").read_text(encoding="utf-8")),
        json.loads((out_path / "warnings.json").read_text(encoding="utf-8")),
    )


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path, rows):
    lines = []
    for row in rows:
        if isinstance(row, str):
            lines.append(row)
        else:
            lines.append(json.dumps(row, separators=(",", ":")))
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def posix(path):
    return Path(path).as_posix()


def test_bundled_fixture_reconciles_retention_summary_records_and_actions():
    """The bundled manifests exercise duplicate winners, exceptions, modes, unknown classes, and actions."""
    report, plan, warnings = run_cli()

    assert report["generated_at"] == "2026-06-26T00:00:00Z"
    assert report["summary"] == {
        "records_total": 8,
        "actions_total": 4,
        "warnings_total": 11,
        "records_by_status": {
            "cleanup_blocked": 1,
            "delete_due": 2,
            "exception_retained": 1,
            "group_blocked": 1,
            "needs_review": 1,
            "permission_review": 1,
            "quarantine_due": 1,
        },
        "bytes_by_status": {
            "cleanup_blocked": 600,
            "delete_due": 1400,
            "exception_retained": 3000,
            "group_blocked": 700,
            "needs_review": 25,
            "permission_review": 2000,
            "quarantine_due": 50,
        },
    }
    assert warnings["generated_at"] == report["generated_at"]

    records = {record["path"]: record for record in report["records"]}
    assert list(records) == sorted(records)

    batch = records["/srv/app/exports/customer/batch-001.csv"]
    assert batch["status"] == "delete_due"
    assert batch["source_path"] == "/app/manifests/site-a/files.jsonl"
    assert batch["source_line"] == 1
    assert batch["mode_compliant"] is True
    assert batch["age_days"] == 67
    assert batch["base_deadline"] == "2026-06-04T00:00:00Z"
    assert batch["effective_deadline"] == "2026-06-04T00:00:00Z"
    assert batch["size_bytes"] == 1000

    blocked = records["/srv/app/exports/customer/blocked/stale.csv"]
    assert blocked["class"] == "customer_export"
    assert blocked["status"] == "cleanup_blocked"
    assert blocked["blocked_by"] == "BLK-EXPORT-LEGAL"
    assert blocked["policy_id"] == "customer_export"
    assert blocked["mode_compliant"] is False
    assert blocked["effective_deadline"] == "2026-06-04T00:00:00Z"

    hold = records["/srv/app/exports/customer/hold/legal-123.csv"]
    assert hold["status"] == "permission_review"
    assert hold["exception_id"] == "EX-HOLD"
    assert hold["base_deadline"] == "2026-06-04T00:00:00Z"
    assert hold["effective_deadline"] == "2026-07-19T00:00:00Z"
    assert hold["mode_compliant"] is False

    audit = records["/srv/app/audit/special/june.log"]
    assert audit["status"] == "exception_retained"
    assert audit["exception_id"] == "EX-MODE"
    assert audit["mode_compliant"] is True
    assert audit["retention_group"] == "case-77"
    assert audit["effective_deadline"] == "2026-09-28T00:00:00Z"

    grouped = records["/srv/app/audit/archive/followup.log"]
    assert grouped["status"] == "group_blocked"
    assert grouped["retention_group"] == "case-77"
    assert grouped["blocked_by"] == "group:case-77:/srv/app/audit/special/june.log"
    assert grouped["mode_compliant"] is True

    unknown = records["/srv/app/misc/readme.txt"]
    assert unknown["status"] == "needs_review"
    assert unknown["policy_id"] == ""
    assert unknown["effective_deadline"] is None
    assert unknown["exception_id"] == ""

    actions = {(row["action"], row["path"]): row for row in plan["actions"]}
    assert [(row["wave"], row["action"]) for row in plan["actions"]] == [(1, "chmod"), (1, "delete"), (1, "delete"), (1, "quarantine")]
    assert actions[("chmod", "/srv/app/exports/customer/hold/legal-123.csv")]["reason_codes"] == [
        "mode_too_permissive"
    ]
    assert actions[("delete", "/srv/app/exports/customer/batch-001.csv")]["reason_codes"] == [
        "retention_expired"
    ]
    assert actions[("delete", "/srv/app/cache/tmp/blob.tmp")]["reason_codes"] == [
        "retention_expired",
        "mode_too_permissive",
    ]
    assert actions[("quarantine", "/srv/app/secrets/leak.txt")]["due_at"] == "2026-06-26T00:00:00Z"


def test_bundled_warnings_are_documented_sorted_and_source_attributed():
    """Warnings must use documented codes, severities, detail templates, line metadata, and sort keys."""
    _, _, warnings_file = run_cli()
    warnings = warnings_file["warnings"]

    observed_sort = [
        (row["code"], row["subject_path"], row["source_path"], row["source_line"], row["detail"])
        for row in warnings
    ]
    assert observed_sort == sorted(observed_sort)
    assert [(row["code"], row["severity"]) for row in warnings] == [
        ("cleanup_blocked", "warning"),
        ("duplicate_manifest", "warning"),
        ("expired_exception", "warning"),
        ("group_blocked", "warning"),
        ("invalid_manifest", "error"),
        ("malformed_manifest", "error"),
        ("mode_too_permissive", "warning"),
        ("mode_too_permissive", "warning"),
        ("mode_too_permissive", "warning"),
        ("mode_too_permissive", "warning"),
        ("unknown_class", "error"),
    ]
    assert warnings[0] == {
        "code": "cleanup_blocked",
        "severity": "warning",
        "subject_path": "/srv/app/exports/customer/blocked/stale.csv",
        "source_path": "/app/manifests/site-a/files.jsonl",
        "source_line": 9,
        "detail": "cleanup blocked by BLK-EXPORT-LEGAL for /srv/app/exports/customer/blocked/stale.csv; action delete",
    }
    assert warnings[1] == {
        "code": "duplicate_manifest",
        "severity": "warning",
        "subject_path": "/srv/app/exports/customer/batch-001.csv",
        "source_path": "/app/manifests/site-b/duplicates.jsonl",
        "source_line": 1,
        "detail": "duplicate path /srv/app/exports/customer/batch-001.csv; kept /app/manifests/site-a/files.jsonl:1",
    }
    assert warnings[2]["detail"] == "expired exception EX-EXPIRED ignored for /srv/app/cache/tmp/blob.tmp"
    assert warnings[3] == {
        "code": "group_blocked",
        "severity": "warning",
        "subject_path": "/srv/app/audit/archive/followup.log",
        "source_path": "/app/manifests/site-a/files.jsonl",
        "source_line": 10,
        "detail": "group case-77 blocked archive for /srv/app/audit/archive/followup.log due to /srv/app/audit/special/june.log",
    }
    assert warnings[4]["detail"] == "invalid manifest record: mode must be four octal digits"
    assert warnings[4]["subject_path"] == "/srv/app/audit/bad-mode.log"
    assert warnings[5] == {
        "code": "malformed_manifest",
        "severity": "error",
        "subject_path": "",
        "source_path": "/app/manifests/site-a/files.jsonl",
        "source_line": 7,
        "detail": "malformed JSON at /app/manifests/site-a/files.jsonl:7",
    }
    mode_details = [(row["subject_path"], row["detail"]) for row in warnings if row["code"] == "mode_too_permissive"]
    assert mode_details == [
        ("/srv/app/cache/tmp/blob.tmp", "mode 0666 exceeds max 0660"),
        ("/srv/app/exports/customer/blocked/stale.csv", "mode 0644 exceeds max 0640"),
        ("/srv/app/exports/customer/hold/legal-123.csv", "mode 0644 exceeds max 0640"),
        ("/srv/app/secrets/leak.txt", "mode 0644 exceeds max 0600"),
    ]


def test_dynamic_duplicate_tie_breakers_and_stale_cleanup(tmp_path):
    """Dynamic manifests verify duplicate tie-break ordering and output reruns without bundled answers."""
    config = tmp_path / "policy.json"
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "old.json").write_text('{"stale":true}\n', encoding="utf-8")
    (out / "notes.txt").write_text("keep\n", encoding="utf-8")
    write_json(
        config,
        {
            "evaluation_time": "2026-06-26T00:00:00Z",
            "defaults": {"retention_days": 30, "max_mode": "0640", "delete_action": "delete"},
            "classes": {"log": {"policy_id": "log", "retention_days": 20, "max_mode": "0640", "delete_action": "archive"}},
            "exceptions": [],
        },
    )
    common = {
        "path": "/var/log/app/a.log",
        "record_type": "file",
        "class": "log",
        "modified_at": "2026-06-01T00:00:00Z",
        "mode": "0640",
        "size_bytes": 10,
        "source_rank": 2,
        "scanned_at": "2026-06-20T00:00:00Z",
    }
    write_jsonl(manifests / "b.jsonl", [{**common, "owner": "discarded"}])
    write_jsonl(manifests / "a.jsonl", [{**common, "owner": "kept"}])

    report, plan, warnings = run_cli(config, manifests, out)

    assert {entry.name for entry in out.iterdir()} == {*REQUIRED_JSON, "notes.txt"}
    assert (out / "notes.txt").read_text(encoding="utf-8") == "keep\n"
    assert not (out / "old.json").exists()
    assert report["records"][0]["owner"] == "kept"
    assert report["records"][0]["source_path"] == posix(manifests / "a.jsonl")
    assert report["records"][0]["status"] == "archive_due"
    assert plan["actions"][0]["action"] == "archive"
    assert warnings["warnings"] == [
        {
            "code": "duplicate_manifest",
            "severity": "warning",
            "subject_path": "/var/log/app/a.log",
            "source_path": posix(manifests / "b.jsonl"),
            "source_line": 1,
            "detail": f"duplicate path /var/log/app/a.log; kept {posix(manifests / 'a.jsonl')}:1",
        }
    ]


def test_dynamic_exception_windows_permissions_and_boundary_behavior(tmp_path):
    """Start-inclusive and end-exclusive exception windows must interact correctly with mode suppression."""
    config = tmp_path / "policy.json"
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    out = tmp_path / "out"
    write_json(
        config,
        {
            "evaluation_time": "2026-06-26T00:00:00Z",
            "defaults": {"retention_days": 30, "max_mode": "0640", "delete_action": "delete"},
            "classes": {"log": {"policy_id": "log", "retention_days": 20, "max_mode": "0640", "delete_action": "archive"}},
            "exceptions": [
                {
                    "exception_id": "EX-END",
                    "path_prefix": "/data/end/",
                    "class": "log",
                    "starts_at": "2026-06-01T00:00:00Z",
                    "ends_at": "2026-06-26T00:00:00Z",
                    "retention_days": 200,
                    "allow_mode": True,
                },
                {
                    "exception_id": "EX-START",
                    "path_prefix": "/data/start/",
                    "class": "log",
                    "starts_at": "2026-06-26T00:00:00Z",
                    "ends_at": "2026-07-01T00:00:00Z",
                    "retention_days": 200,
                    "allow_mode": True,
                },
            ],
        },
    )
    write_jsonl(
        manifests / "files.jsonl",
        [
            {
                "path": "/data/end/file.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-20T00:00:00Z",
                "mode": "0666",
                "owner": "ops",
                "group": "ops",
                "size_bytes": 3,
            },
            {
                "path": "/data/start/file.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-20T00:00:00Z",
                "mode": "0666",
                "owner": "ops",
                "group": "ops",
                "size_bytes": 4,
            },
        ],
    )

    report, plan, warnings = run_cli(config, manifests, out)

    records = {record["path"]: record for record in report["records"]}
    assert records["/data/end/file.log"]["status"] == "permission_review"
    assert records["/data/end/file.log"]["exception_id"] == ""
    assert records["/data/end/file.log"]["mode_compliant"] is False
    assert records["/data/start/file.log"]["status"] == "exception_retained"
    assert records["/data/start/file.log"]["exception_id"] == "EX-START"
    assert records["/data/start/file.log"]["mode_compliant"] is True
    assert plan["actions"] == [
        {
            "wave": 1,
            "action": "chmod",
            "path": "/data/end/file.log",
            "policy_id": "log",
            "exception_id": "",
            "reason_codes": ["mode_too_permissive"],
            "due_at": "2026-06-26T00:00:00Z",
            "source_path": posix(manifests / "files.jsonl"),
            "source_line": 1,
        }
    ]
    assert [(row["code"], row["subject_path"], row["detail"]) for row in warnings["warnings"]] == [
        ("expired_exception", "/data/end/file.log", "expired exception EX-END ignored for /data/end/file.log"),
        ("mode_too_permissive", "/data/end/file.log", "mode 0666 exceeds max 0640"),
    ]


def test_dynamic_malformed_rows_preserve_valid_peers_and_unknown_classes(tmp_path):
    """Malformed and invalid rows should not prevent valid peers or unknown-class report rows from being emitted."""
    config = tmp_path / "policy.json"
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    out = tmp_path / "out"
    write_json(
        config,
        {
            "evaluation_time": "2026-06-26T00:00:00Z",
            "defaults": {"retention_days": 30, "max_mode": "0640", "delete_action": "delete"},
            "classes": {"cache": {"policy_id": "cache", "retention_days": 7, "max_mode": "0660", "delete_action": "delete"}},
            "exceptions": [],
        },
    )
    write_jsonl(
        manifests / "mixed.jsonl",
        [
            "{broken json",
            {
                "path": "/tmp/cache/a.bin",
                "record_type": "file",
                "class": "cache",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0660",
                "owner": "cache",
                "group": "ops",
                "size_bytes": 12,
            },
            {
                "path": "/tmp/cache/b.bin",
                "record_type": "file",
                "class": "unknown_cache",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0660",
                "owner": "cache",
                "group": "ops",
                "size_bytes": 13,
            },
            {
                "path": "/tmp/cache/c.bin",
                "record_type": "directory",
                "class": "cache",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0660",
                "owner": "cache",
                "group": "ops",
                "size_bytes": 14,
            },
        ],
    )

    report, plan, warnings = run_cli(config, manifests, out)

    records = {record["path"]: record for record in report["records"]}
    assert set(records) == {"/tmp/cache/a.bin", "/tmp/cache/b.bin"}
    assert records["/tmp/cache/a.bin"]["status"] == "delete_due"
    assert records["/tmp/cache/b.bin"]["status"] == "needs_review"
    assert plan["actions"] == [
        {
            "wave": 1,
            "action": "delete",
            "path": "/tmp/cache/a.bin",
            "policy_id": "cache",
            "exception_id": "",
            "reason_codes": ["retention_expired"],
            "due_at": "2026-06-08T00:00:00Z",
            "source_path": posix(manifests / "mixed.jsonl"),
            "source_line": 2,
        }
    ]
    assert [(row["code"], row["subject_path"], row["source_line"], row["detail"]) for row in warnings["warnings"]] == [
        ("invalid_manifest", "/tmp/cache/c.bin", 4, "invalid manifest record: record_type must be file"),
        ("malformed_manifest", "", 1, f"malformed JSON at {posix(manifests / 'mixed.jsonl')}:1"),
        ("unknown_class", "/tmp/cache/b.bin", 3, "unknown class unknown_cache"),
    ]



def test_dynamic_class_aliases_cleanup_blocks_and_cross_output_consistency(tmp_path):
    """Class aliases and cleanup blocks must interact with warnings, statuses, and action suppression."""
    config = tmp_path / "policy.json"
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    out = tmp_path / "out"
    write_json(
        config,
        {
            "evaluation_time": "2026-06-26T00:00:00Z",
            "defaults": {"retention_days": 30, "max_mode": "0640", "delete_action": "delete"},
            "classes": {
                "log": {
                    "policy_id": "log-pol",
                    "retention_days": 10,
                    "max_mode": "0640",
                    "delete_action": "archive",
                }
            },
            "class_aliases": {"rotated_log": "log"},
            "exceptions": [],
            "cleanup_blocks": [
                {
                    "blocker_id": "BLK-LEGAL-OLD",
                    "path_prefix": "/records/legal/",
                    "class": "log",
                    "starts_at": "2026-06-01T00:00:00Z",
                    "ends_at": "2026-07-01T00:00:00Z",
                    "applies_to": ["archive"],
                },
                {
                    "blocker_id": "BLK-LEGAL-LATE",
                    "path_prefix": "/records/legal/",
                    "class": "log",
                    "starts_at": "2026-06-10T00:00:00Z",
                    "ends_at": "2026-07-01T00:00:00Z",
                    "applies_to": ["archive"],
                },
            ],
        },
    )
    write_jsonl(
        manifests / "records.jsonl",
        [
            {
                "path": "/records/legal/old.log",
                "record_type": "file",
                "class": "rotated_log",
                "modified_at": "2026-05-01T00:00:00Z",
                "mode": "0666",
                "size_bytes": 9,
            },
            {
                "path": "/records/open/old.log",
                "record_type": "file",
                "class": "rotated_log",
                "modified_at": "2026-05-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 10,
            },
            {
                "path": "/records/legal/chmod-only.log",
                "record_type": "file",
                "class": "rotated_log",
                "modified_at": "2026-06-25T00:00:00Z",
                "mode": "0666",
                "size_bytes": 8,
            },
        ],
    )

    report, plan, warnings = run_cli(config, manifests, out)

    records = {record["path"]: record for record in report["records"]}
    assert report["summary"]["records_by_status"] == {
        "archive_due": 1,
        "cleanup_blocked": 1,
        "permission_review": 1,
    }
    assert records["/records/legal/old.log"]["class"] == "log"
    assert records["/records/legal/old.log"]["status"] == "cleanup_blocked"
    assert records["/records/legal/old.log"]["blocked_by"] == "BLK-LEGAL-LATE"
    assert records["/records/legal/old.log"]["mode_compliant"] is False
    assert records["/records/open/old.log"]["status"] == "archive_due"
    assert records["/records/legal/chmod-only.log"]["status"] == "permission_review"
    assert records["/records/legal/chmod-only.log"]["blocked_by"] == ""

    assert [(row["action"], row["path"], row["reason_codes"]) for row in plan["actions"]] == [
        ("archive", "/records/open/old.log", ["retention_expired"]),
        ("chmod", "/records/legal/chmod-only.log", ["mode_too_permissive"]),
    ]
    assert [(row["code"], row["subject_path"], row["detail"]) for row in warnings["warnings"]] == [
        (
            "cleanup_blocked",
            "/records/legal/old.log",
            "cleanup blocked by BLK-LEGAL-LATE for /records/legal/old.log; action archive",
        ),
        (
            "mode_too_permissive",
            "/records/legal/chmod-only.log",
            "mode 0666 exceeds max 0640",
        ),
        (
            "mode_too_permissive",
            "/records/legal/old.log",
            "mode 0666 exceeds max 0640",
        ),
    ]



def test_dynamic_retention_group_holds_run_after_cleanup_blocks(tmp_path):
    """Retention groups must suppress peer cleanup actions after exception and cleanup-block status is known."""
    config = tmp_path / "policy.json"
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    out = tmp_path / "out"
    write_json(
        config,
        {
            "evaluation_time": "2026-06-26T00:00:00Z",
            "defaults": {"retention_days": 30, "max_mode": "0640", "delete_action": "delete"},
            "classes": {
                "log": {
                    "policy_id": "log-pol",
                    "retention_days": 5,
                    "max_mode": "0640",
                    "delete_action": "archive",
                }
            },
            "class_aliases": {"rotated_log": "log"},
            "exceptions": [
                {
                    "exception_id": "EX-GROUP-HOLD",
                    "path_prefix": "/cases/hold/",
                    "class": "log",
                    "starts_at": "2026-06-20T00:00:00Z",
                    "ends_at": "2026-07-20T00:00:00Z",
                    "retention_days": 30,
                    "allow_mode": True,
                }
            ],
            "cleanup_blocks": [
                {
                    "blocker_id": "BLK-GROUP-PROTECTOR",
                    "path_prefix": "/cases/blocked/protector/",
                    "class": "log",
                    "starts_at": "2026-06-01T00:00:00Z",
                    "ends_at": "2026-07-01T00:00:00Z",
                    "applies_to": ["archive"],
                }
            ],
        },
    )
    write_jsonl(
        manifests / "groups.jsonl",
        [
            {
                "path": "/cases/hold/protected.log",
                "record_type": "file",
                "class": "rotated_log",
                "modified_at": "2026-06-15T00:00:00Z",
                "mode": "0666",
                "size_bytes": 11,
                "retention_group": "g-alpha",
            },
            {
                "path": "/cases/due/stale.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 12,
                "retention_group": "g-alpha",
            },
            {
                "path": "/cases/blocked/protector/stale.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 13,
                "retention_group": "g-beta",
            },
            {
                "path": "/cases/blocked/peer/stale.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 14,
                "retention_group": "g-beta",
            },
            {
                "path": "/cases/open/stale.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 15,
                "retention_group": "g-gamma",
            },
        ],
    )

    report, plan, warnings = run_cli(config, manifests, out)

    records = {record["path"]: record for record in report["records"]}
    assert report["summary"]["records_by_status"] == {
        "archive_due": 1,
        "cleanup_blocked": 1,
        "exception_retained": 1,
        "group_blocked": 2,
    }
    assert records["/cases/hold/protected.log"]["class"] == "log"
    assert records["/cases/hold/protected.log"]["status"] == "exception_retained"
    assert records["/cases/hold/protected.log"]["mode_compliant"] is True
    assert records["/cases/due/stale.log"]["status"] == "group_blocked"
    assert records["/cases/due/stale.log"]["blocked_by"] == "group:g-alpha:/cases/hold/protected.log"
    assert records["/cases/blocked/protector/stale.log"]["status"] == "cleanup_blocked"
    assert records["/cases/blocked/protector/stale.log"]["blocked_by"] == "BLK-GROUP-PROTECTOR"
    assert records["/cases/blocked/peer/stale.log"]["status"] == "group_blocked"
    assert records["/cases/blocked/peer/stale.log"]["blocked_by"] == "group:g-beta:/cases/blocked/protector/stale.log"

    assert [(row["action"], row["path"]) for row in plan["actions"]] == [
        ("archive", "/cases/open/stale.log")
    ]
    assert [(row["code"], row["subject_path"], row["detail"]) for row in warnings["warnings"]] == [
        (
            "cleanup_blocked",
            "/cases/blocked/protector/stale.log",
            "cleanup blocked by BLK-GROUP-PROTECTOR for /cases/blocked/protector/stale.log; action archive",
        ),
        (
            "group_blocked",
            "/cases/blocked/peer/stale.log",
            "group g-beta blocked archive for /cases/blocked/peer/stale.log due to /cases/blocked/protector/stale.log",
        ),
        (
            "group_blocked",
            "/cases/due/stale.log",
            "group g-alpha blocked archive for /cases/due/stale.log due to /cases/hold/protected.log",
        ),
    ]



def test_dynamic_cleanup_dependency_cycles_and_capacity_waves(tmp_path):
    """Cleanup dependency graphs, cycles, ignored dependencies, and per-action wave capacity must agree."""
    config = tmp_path / "policy.json"
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    out = tmp_path / "out"
    write_json(
        config,
        {
            "evaluation_time": "2026-06-26T00:00:00Z",
            "defaults": {"retention_days": 30, "max_mode": "0640", "delete_action": "delete"},
            "classes": {
                "log": {
                    "policy_id": "log-pol",
                    "retention_days": 5,
                    "max_mode": "0640",
                    "delete_action": "archive",
                }
            },
            "cleanup_capacity": {"archive": 1},
            "exceptions": [],
            "cleanup_blocks": [],
        },
    )
    write_jsonl(
        manifests / "graph.jsonl",
        [
            {
                "path": "/graph/missing-dep.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 10,
                "cleanup_after": ["/graph/no-action.log", "relative/path", "/graph/no-such.log"],
            },
            {
                "path": "/graph/root.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 11,
            },
            {
                "path": "/graph/child-a.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 12,
                "cleanup_after": ["/graph/root.log"],
            },
            {
                "path": "/graph/child-b.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 13,
                "cleanup_after": ["/graph/root.log"],
            },
            {
                "path": "/graph/grandchild.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 14,
                "cleanup_after": ["/graph/child-b.log", "/graph/child-a.log"],
            },
            {
                "path": "/graph/cycle-a.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 15,
                "cleanup_after": ["/graph/cycle-b.log"],
            },
            {
                "path": "/graph/cycle-b.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 16,
                "cleanup_after": ["/graph/cycle-a.log"],
            },
            {
                "path": "/graph/no-action.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-25T00:00:00Z",
                "mode": "0640",
                "size_bytes": 17,
            },
        ],
    )

    report, plan, warnings = run_cli(config, manifests, out)

    records = {record["path"]: record for record in report["records"]}
    assert report["summary"]["records_by_status"] == {
        "archive_due": 5,
        "dependency_blocked": 2,
        "retained": 1,
    }
    assert report["summary"]["bytes_by_status"] == {
        "archive_due": 60,
        "dependency_blocked": 31,
        "retained": 17,
    }
    assert records["/graph/cycle-a.log"]["status"] == "dependency_blocked"
    assert records["/graph/cycle-a.log"]["blocked_by"] == "cycle:/graph/cycle-a.log"
    assert records["/graph/cycle-b.log"]["status"] == "dependency_blocked"
    assert records["/graph/cycle-b.log"]["blocked_by"] == "cycle:/graph/cycle-a.log"
    assert records["/graph/no-action.log"]["status"] == "retained"

    assert [(row["wave"], row["action"], row["path"]) for row in plan["actions"]] == [
        (1, "archive", "/graph/missing-dep.log"),
        (2, "archive", "/graph/root.log"),
        (3, "archive", "/graph/child-a.log"),
        (4, "archive", "/graph/child-b.log"),
        (5, "archive", "/graph/grandchild.log"),
    ]
    assert all(row["reason_codes"] == ["retention_expired"] for row in plan["actions"])
    assert [(row["code"], row["subject_path"], row["detail"]) for row in warnings["warnings"]] == [
        (
            "dependency_cycle",
            "/graph/cycle-a.log",
            "cleanup dependency cycle /graph/cycle-a.log includes /graph/cycle-a.log",
        ),
        (
            "dependency_cycle",
            "/graph/cycle-b.log",
            "cleanup dependency cycle /graph/cycle-a.log includes /graph/cycle-b.log",
        ),
    ]


def test_dynamic_cleanup_byte_budgets_split_ready_actions_after_dependencies(tmp_path):
    """Byte budgets combine with action count limits and dependency readiness when assigning waves."""
    config = tmp_path / "policy.json"
    manifests = tmp_path / "manifests"
    manifests.mkdir()
    out = tmp_path / "out"
    write_json(
        config,
        {
            "evaluation_time": "2026-06-26T00:00:00Z",
            "defaults": {"retention_days": 30, "max_mode": "0640", "delete_action": "delete"},
            "classes": {
                "log": {
                    "policy_id": "log-pol",
                    "retention_days": 5,
                    "max_mode": "0640",
                    "delete_action": "archive",
                }
            },
            "cleanup_capacity": {"archive": 2},
            "cleanup_byte_capacity": {"archive": 100},
            "exceptions": [],
            "cleanup_blocks": [],
        },
    )
    write_jsonl(
        manifests / "budget.jsonl",
        [
            {
                "path": "/budget/archive-a.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 70,
            },
            {
                "path": "/budget/archive-b.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 50,
            },
            {
                "path": "/budget/archive-c.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 40,
                "cleanup_after": ["/budget/archive-a.log", "/budget/archive-b.log"],
            },
            {
                "path": "/budget/archive-d.log",
                "record_type": "file",
                "class": "log",
                "modified_at": "2026-06-01T00:00:00Z",
                "mode": "0640",
                "size_bytes": 20,
            },
        ],
    )

    report, plan, warnings = run_cli(config, manifests, out)

    assert report["summary"]["records_by_status"] == {"archive_due": 4}
    assert report["summary"]["bytes_by_status"] == {"archive_due": 180}
    assert warnings["warnings"] == []
    assert [(row["wave"], row["action"], row["path"]) for row in plan["actions"]] == [
        (1, "archive", "/budget/archive-a.log"),
        (1, "archive", "/budget/archive-d.log"),
        (2, "archive", "/budget/archive-b.log"),
        (3, "archive", "/budget/archive-c.log"),
    ]
    records = {record["path"]: record for record in report["records"]}
    sizes_by_path = {path: record["size_bytes"] for path, record in records.items()}
    for wave in {row["wave"] for row in plan["actions"]}:
        archived_bytes = sum(
            sizes_by_path[row["path"]]
            for row in plan["actions"]
            if row["wave"] == wave and row["action"] == "archive"
        )
        assert archived_bytes <= 100
    assert all(row["reason_codes"] == ["retention_expired"] for row in plan["actions"])

