"""Verifier for milestone 2 event summarization behavior."""

import json
import subprocess
from pathlib import Path


APP = Path("/app")


def write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


class TestMilestone2:
    def test_summary_dedupes_corrections_aliases_and_unknowns(self):
        """Summaries should use aliases, correction replacements, sorted sources, and dropped counts."""
        work = APP / "tmp" / "m2"
        work.mkdir(parents=True, exist_ok=True)
        config_path = work / "rules.json"
        events_path = work / "events.jsonl"
        out_path = work / "summary.json"

        # Arrange a config whose definition order differs from the required output sort order.
        config_path.write_text(
            json.dumps(
                {
                    "version": 7,
                    "services": [
                        {
                            "name": "Data Worker",
                            "aliases": ["worker"],
                            "tier": "standard",
                            "weight": 0.4,
                            "retention_days": 45,
                        },
                        {
                            "name": "Checkout API",
                            "aliases": ["checkout", "co api"],
                            "tier": "critical",
                            "weight": 0.9,
                            "retention_days": 90,
                        },
                    ],
                }
            )
        )

        # Arrange events that exercise alias lookup, dedupe ordering, corrections, and drops together.
        write_jsonl(
            events_path,
            [
                {
                    "event_id": "e-1",
                    "service": "checkout",
                    "occurred_at": "2026-05-01T10:00:00Z",
                    "metric": "latency_ms",
                    "value": 100,
                    "source": "edge-a",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "e-1",
                    "service": "CHECKOUT API",
                    "occurred_at": "2026-05-01T10:01:00Z",
                    "metric": "latency_ms",
                    "value": 120,
                    "source": "edge-a",
                    "sequence": 2,
                    "kind": "measurement",
                },
                {
                    "event_id": "e-2",
                    "service": "co_api",
                    "occurred_at": "2026-05-01T10:02:00Z",
                    "metric": "latency_ms",
                    "value": 80,
                    "source": "edge-b",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "e-3",
                    "service": "worker",
                    "occurred_at": "2026-05-01T10:03:00Z",
                    "metric": "jobs",
                    "value": 5,
                    "source": "batch",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "tie-1",
                    "service": "checkout",
                    "occurred_at": "2026-05-01T10:07:00Z",
                    "metric": "latency_ms",
                    "value": 110,
                    "source": "edge-c",
                    "sequence": 5,
                    "kind": "measurement",
                },
                {
                    "event_id": "tie-1",
                    "service": "checkout",
                    "occurred_at": "2026-05-01T10:06:00Z",
                    "metric": "latency_ms",
                    "value": 999,
                    "source": "edge-c",
                    "sequence": 5,
                    "kind": "measurement",
                },
                {
                    "event_id": "e-6",
                    "service": "worker",
                    "occurred_at": "2026-05-01T10:08:00Z",
                    "metric": "jobs",
                    "value": 50,
                    "source": "batch",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "e-8",
                    "service": "worker",
                    "occurred_at": "2026-05-01T10:08:30Z",
                    "metric": "jobs",
                    "value": 99,
                    "source": "audit",
                    "sequence": 1,
                    "kind": "correction",
                    "correction_of": "e-6",
                },
                {
                    "event_id": "e-7",
                    "service": "worker",
                    "occurred_at": "2026-05-01T10:09:00Z",
                    "metric": "jobs",
                    "value": 7,
                    "source": "ops",
                    "sequence": 2,
                    "kind": "correction",
                    "correction_of": "e-6",
                },
                {
                    "event_id": "e-4",
                    "service": "checkout-api",
                    "occurred_at": "2026-05-01T10:04:00Z",
                    "metric": "latency_ms",
                    "value": 70,
                    "source": "edge-b",
                    "sequence": 3,
                    "kind": "correction",
                    "correction_of": "e-2",
                },
                {
                    "event_id": "chain-root",
                    "service": "worker",
                    "occurred_at": "2026-05-01T10:09:30Z",
                    "metric": "jobs",
                    "value": 100,
                    "source": "batch",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "chain-final",
                    "service": "Data Worker",
                    "occurred_at": "2026-05-01T10:12:00Z",
                    "metric": "jobs",
                    "value": 12,
                    "source": "quality",
                    "sequence": 6,
                    "kind": "correction",
                    "correction_of": "chain-middle",
                },
                {
                    "event_id": "chain-middle",
                    "service": "worker",
                    "occurred_at": "2026-05-01T10:11:00Z",
                    "metric": "jobs",
                    "value": 9,
                    "source": "audit",
                    "sequence": 5,
                    "kind": "correction",
                    "correction_of": "chain-root",
                },
                {
                    "event_id": "e-zero",
                    "service": "co api",
                    "occurred_at": "2026-05-01T10:10:00Z",
                    "metric": "latency_ms",
                    "value": 0,
                    "source": "edge-zero",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "e-5",
                    "service": "unknown svc",
                    "occurred_at": "2026-05-01T10:05:00Z",
                    "metric": "latency_ms",
                    "value": 999,
                    "source": "edge-z",
                    "sequence": 1,
                    "kind": "measurement",
                },
            ],
        )

        # Run the CLI against arbitrary supplied paths rather than pre-staged default files.
        result = subprocess.run(
            [
                "go",
                "run",
                "./cmd/ledger",
                "summarize",
                "--config",
                str(config_path),
                "--events",
                str(events_path),
                "--out",
                str(out_path),
            ],
            cwd=APP,
            text=True,
            capture_output=True,
            timeout=90,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(out_path.read_text())

        # Assert totals first so dropped and effective event accounting failures are easy to locate.
        assert payload["totals"] == {
            "service_count": 2,
            "event_count": 6,
            "dropped_events": 1,
            "suppressed_events": 1,
        }

        # Assert sorted services and per-service metric aggregates.
        assert len(payload["services"]) == 2
        checkout = payload["services"][0]
        worker = payload["services"][1]
        assert checkout["service"] == "checkout-api"
        assert checkout["tier"] == "critical"
        assert checkout["event_count"] == 3
        assert checkout["sources"] == ["edge-a", "edge-b", "edge-c"]
        latency = checkout["metrics"]["latency_ms"]
        assert latency == {"count": 3, "sum": 300, "min": 70, "max": 120, "avg": 100}
        assert worker["service"] == "data-worker"
        assert worker["tier"] == "standard"
        assert worker["event_count"] == 3
        assert worker["sources"] == ["batch", "ops", "quality"]
        assert worker["metrics"]["jobs"] == {"count": 3, "sum": 24, "min": 5, "max": 12, "avg": 8}

    def test_summary_applies_retention_after_corrections_per_service(self):
        """Retention windows should be anchored per service after correction replacement."""
        work = APP / "tmp" / "m2_retention"
        work.mkdir(parents=True, exist_ok=True)
        config_path = work / "rules.json"
        events_path = work / "events.jsonl"
        out_path = work / "summary.json"

        config_path.write_text(
            json.dumps(
                {
                    "version": 11,
                    "services": [
                        {
                            "name": "Audit API",
                            "aliases": ["audit"],
                            "tier": "critical",
                            "weight": 0.8,
                            "retention_days": 2,
                        },
                        {
                            "name": "Batch Worker",
                            "aliases": ["worker"],
                            "tier": "standard",
                            "weight": 0.3,
                            "retention_days": 5,
                        },
                    ],
                }
            )
        )
        write_jsonl(
            events_path,
            [
                {
                    "event_id": "a-stale",
                    "service": "audit",
                    "occurred_at": "2026-05-01T13:00:00Z",
                    "metric": "latency_ms",
                    "value": 77,
                    "source": "sensor-a",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "a-old",
                    "service": "audit",
                    "occurred_at": "2026-05-01T14:00:00Z",
                    "metric": "latency_ms",
                    "value": 100,
                    "source": "sensor-old",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "a-boundary",
                    "service": "Audit API",
                    "occurred_at": "2026-05-02T13:00:00Z",
                    "metric": "latency_ms",
                    "value": 20,
                    "source": "sensor-b",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "a-new",
                    "service": "audit",
                    "occurred_at": "2026-05-04T13:00:00Z",
                    "metric": "latency_ms",
                    "value": 40,
                    "source": "sensor-c",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "a-zero-late",
                    "service": "audit",
                    "occurred_at": "2026-05-10T13:00:00Z",
                    "metric": "latency_ms",
                    "value": 0,
                    "source": "sensor-zero",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "a-fix",
                    "service": "audit",
                    "occurred_at": "2026-05-04T13:00:00Z",
                    "metric": "latency_ms",
                    "value": 6,
                    "source": "audit-fix",
                    "sequence": 2,
                    "kind": "correction",
                    "correction_of": "a-old",
                },
                {
                    "event_id": "b-stale",
                    "service": "worker",
                    "occurred_at": "2026-05-04T12:00:00Z",
                    "metric": "jobs",
                    "value": 8,
                    "source": "batch-old",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "b-current",
                    "service": "Batch Worker",
                    "occurred_at": "2026-05-10T12:00:00Z",
                    "metric": "jobs",
                    "value": 2,
                    "source": "batch-current",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "unknown-1",
                    "service": "missing service",
                    "occurred_at": "2026-05-10T12:01:00Z",
                    "metric": "latency_ms",
                    "value": 999,
                    "source": "sensor-z",
                    "sequence": 1,
                    "kind": "measurement",
                },
            ],
        )

        result = subprocess.run(
            [
                "go",
                "run",
                "./cmd/ledger",
                "summarize",
                "--config",
                str(config_path),
                "--events",
                str(events_path),
                "--out",
                str(out_path),
            ],
            cwd=APP,
            text=True,
            capture_output=True,
            timeout=90,
        )

        assert result.returncode == 0, result.stderr
        payload = json.loads(out_path.read_text())
        assert payload["totals"] == {
            "service_count": 2,
            "event_count": 4,
            "dropped_events": 1,
            "suppressed_events": 1,
        }

        audit = payload["services"][0]
        batch = payload["services"][1]
        assert audit["service"] == "audit-api"
        assert audit["event_count"] == 3
        assert audit["sources"] == ["audit-fix", "sensor-b", "sensor-c"]
        assert audit["metrics"]["latency_ms"] == {
            "count": 3,
            "sum": 66,
            "min": 6,
            "max": 40,
            "avg": 22,
        }
        assert batch["service"] == "batch-worker"
        assert batch["event_count"] == 1
        assert batch["sources"] == ["batch-current"]
        assert batch["metrics"]["jobs"] == {"count": 1, "sum": 2, "min": 2, "max": 2, "avg": 2}
