"""Verifier for milestone 5 reconciliation planning behavior."""

import json
from contextlib import contextmanager
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest


APP = Path("/app")


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def write_jsonl(path, rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")


def request_json(url, payload=None, method=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        body = response.read().decode()
        return response.status, response.headers, json.loads(body)




@contextmanager
def running_server():
    port = free_port()
    proc = subprocess.Popen(
        ["go", "run", "./cmd/ledger", "serve", "--addr", f"127.0.0.1:{port}"],
        cwd=APP,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        deadline = time.time() + 30

        while time.time() < deadline:
            try:
                status, _, health = request_json(f"{base}/health")
                if status == 200 and health == {"ok": True}:
                    break
            except Exception:
                time.sleep(0.25)
        else:
            raise AssertionError("server did not become healthy")

        yield base
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def assert_http_error(url, expected_status, payload=None, raw_data=None):
    if raw_data is not None:
        req = urllib.request.Request(
            url,
            data=raw_data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            urllib.request.urlopen(req, timeout=5)
            raise AssertionError(f"request did not return {expected_status}")
        except urllib.error.HTTPError as exc:
            assert exc.code == expected_status
        return

    try:
        request_json(url, payload)
        raise AssertionError(f"request did not return {expected_status}")
    except urllib.error.HTTPError as exc:
        assert exc.code == expected_status


@pytest.fixture(scope="class")
def weighted_reports():
    work = APP / "tmp" / "m5"
    work.mkdir(parents=True, exist_ok=True)
    config_path = work / "rules.json"
    baseline_events = work / "baseline.jsonl"
    candidate_events = work / "candidate.jsonl"

    config_path.write_text(
        json.dumps(
            {
                "version": 10,
                "services": [
                    {
                        "name": "Alpha API",
                        "aliases": ["alpha"],
                        "tier": "standard",
                        "weight": 0.25,
                        "retention_days": 120,
                    },
                    {
                        "name": "Billing API",
                        "aliases": ["billing"],
                        "tier": "standard",
                        "weight": 0.55,
                        "retention_days": 120,
                    },
                    {
                        "name": "Data Worker",
                        "aliases": ["worker"],
                        "tier": "standard",
                        "weight": 0.35,
                        "retention_days": 45,
                    },
                    {
                        "name": "Search API",
                        "aliases": ["search", "lookup"],
                        "tier": "critical",
                        "weight": 0.75,
                        "retention_days": 60,
                    },
                ],
            }
        )
    )
    write_jsonl(
        baseline_events,
        [
            {
                "event_id": "b-backlog",
                "service": "alpha",
                "occurred_at": "2026-05-05T10:59:00Z",
                "metric": "backlog",
                "value": 1,
                "source": "alpha-core",
                "sequence": 1,
                "kind": "measurement",
            },
            {
                "event_id": "b-latency",
                "service": "lookup",
                "occurred_at": "2026-05-05T11:00:00Z",
                "metric": "latency_ms",
                "value": 100,
                "source": "edge-a",
                "sequence": 1,
                "kind": "measurement",
            },
            {
                "event_id": "b-errors",
                "service": "Search API",
                "occurred_at": "2026-05-05T11:01:00Z",
                "metric": "errors",
                "value": 2,
                "source": "edge-a",
                "sequence": 1,
                "kind": "measurement",
            },
            {
                "event_id": "b-jobs",
                "service": "worker",
                "occurred_at": "2026-05-05T11:02:00Z",
                "metric": "jobs",
                "value": 10,
                "source": "batch",
                "sequence": 1,
                "kind": "measurement",
            },
            {
                "event_id": "b-invoices",
                "service": "billing",
                "occurred_at": "2026-05-05T11:03:00Z",
                "metric": "invoices",
                "value": 25,
                "source": "core",
                "sequence": 1,
                "kind": "measurement",
            },
        ],
    )
    write_jsonl(
        candidate_events,
        [
            {
                "event_id": "c-backlog",
                "service": "Alpha API",
                "occurred_at": "2026-05-06T10:59:00Z",
                "metric": "backlog",
                "value": 5,
                "source": "alpha-core",
                "sequence": 1,
                "kind": "measurement",
            },
            {
                "event_id": "c-latency",
                "service": "search",
                "occurred_at": "2026-05-06T11:00:00Z",
                "metric": "latency_ms",
                "value": 160,
                "source": "edge-b",
                "sequence": 1,
                "kind": "measurement",
            },
            {
                "event_id": "c-cache",
                "service": "Search API",
                "occurred_at": "2026-05-06T11:01:00Z",
                "metric": "cache_hits",
                "value": 3,
                "source": "edge-cache",
                "sequence": 1,
                "kind": "measurement",
            },
            {
                "event_id": "c-jobs",
                "service": "worker",
                "occurred_at": "2026-05-06T11:02:00Z",
                "metric": "jobs",
                "value": 4,
                "source": "ops",
                "sequence": 1,
                "kind": "measurement",
            },
            {
                "event_id": "c-invoices",
                "service": "billing",
                "occurred_at": "2026-05-06T11:03:00Z",
                "metric": "invoices",
                "value": 29,
                "source": "core",
                "sequence": 1,
                "kind": "measurement",
            },
        ],
    )

    with running_server() as base:
        report_url = f"{base}/v1/reports"
        _, _, baseline = request_json(
            report_url,
            {"config_path": str(config_path), "events_path": str(baseline_events)},
        )
        _, _, candidate = request_json(
            report_url,
            {"config_path": str(config_path), "events_path": str(candidate_events)},
        )
        yield {
            "base": base,
            "baseline_report_id": baseline["report_id"],
            "candidate_report_id": candidate["report_id"],
        }


def request_reconcile(reports, **overrides):
    payload = {
        "baseline_report_id": reports["baseline_report_id"],
        "candidate_report_id": reports["candidate_report_id"],
    }
    payload.update(overrides)
    return request_json(f"{reports['base']}/v1/reports/reconcile", payload)


class TestMilestone5:
    def test_reconcile_uses_status_specific_tier_sources(self):
        """Each reconcile status should use its documented report tier source."""
        work = APP / "tmp" / "m5_tier_preference"
        work.mkdir(parents=True, exist_ok=True)
        baseline_config = work / "baseline_rules.json"
        candidate_config = work / "candidate_rules.json"
        baseline_events = work / "baseline.jsonl"
        candidate_events = work / "candidate.jsonl"

        service = {
            "name": "Alpha API",
            "aliases": ["alpha"],
            "weight": 0.25,
            "retention_days": 120,
        }
        baseline_config.write_text(
            json.dumps({"version": 10, "services": [service | {"tier": "critical"}]})
        )
        candidate_config.write_text(
            json.dumps({"version": 10, "services": [service | {"tier": "standard"}]})
        )
        write_jsonl(
            baseline_events,
            [
                {
                    "event_id": "b-backlog",
                    "service": "alpha",
                    "occurred_at": "2026-05-05T10:59:00Z",
                    "metric": "backlog",
                    "value": 2,
                    "source": "alpha-core",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "b-legacy-errors",
                    "service": "Alpha API",
                    "occurred_at": "2026-05-05T10:58:00Z",
                    "metric": "legacy_errors",
                    "value": 3,
                    "source": "alpha-core",
                    "sequence": 1,
                    "kind": "measurement",
                }
            ],
        )
        write_jsonl(
            candidate_events,
            [
                {
                    "event_id": "c-backlog",
                    "service": "Alpha API",
                    "occurred_at": "2026-05-06T10:59:00Z",
                    "metric": "backlog",
                    "value": 5,
                    "source": "alpha-core",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "c-cache-hits",
                    "service": "alpha",
                    "occurred_at": "2026-05-06T10:58:00Z",
                    "metric": "cache_hits",
                    "value": 4,
                    "source": "alpha-core",
                    "sequence": 1,
                    "kind": "measurement",
                }
            ],
        )

        port = free_port()
        proc = subprocess.Popen(
            ["go", "run", "./cmd/ledger", "serve", "--addr", f"127.0.0.1:{port}"],
            cwd=APP,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            base = f"http://127.0.0.1:{port}"
            deadline = time.time() + 30

            while time.time() < deadline:
                try:
                    status, _, health = request_json(f"{base}/health")
                    if status == 200 and health == {"ok": True}:
                        break
                except Exception:
                    time.sleep(0.25)
            else:
                raise AssertionError("server did not become healthy")

            report_url = f"{base}/v1/reports"
            _, _, baseline = request_json(
                report_url,
                {"config_path": str(baseline_config), "events_path": str(baseline_events)},
            )
            _, _, candidate = request_json(
                report_url,
                {"config_path": str(candidate_config), "events_path": str(candidate_events)},
            )

            status, _, plan = request_json(
                f"{base}/v1/reports/reconcile",
                {
                    "baseline_report_id": baseline["report_id"],
                    "candidate_report_id": candidate["report_id"],
                },
            )
            assert status == 200
            assert plan["totals"] == {
                "action_count": 3,
                "total_impact_score": 13,
                "by_status": {"new_metric": 1, "regressed": 1, "removed_metric": 1},
                "by_tier": {"critical": 1, "standard": 2},
            }
            assert plan["actions"] == [
                {
                    "service": "alpha-api",
                    "tier": "critical",
                    "metric": "legacy_errors",
                    "status": "removed_metric",
                    "delta_sum": -3,
                    "absolute_delta": 3,
                    "impact_score": 6,
                    "recommendation": "verify_reduction",
                },
                {
                    "service": "alpha-api",
                    "tier": "standard",
                    "metric": "cache_hits",
                    "status": "new_metric",
                    "delta_sum": 4,
                    "absolute_delta": 4,
                    "impact_score": 4,
                    "recommendation": "investigate_candidate",
                },
                {
                    "service": "alpha-api",
                    "tier": "standard",
                    "metric": "backlog",
                    "status": "regressed",
                    "delta_sum": 3,
                    "absolute_delta": 3,
                    "impact_score": 3,
                    "recommendation": "investigate_candidate",
                }
            ]
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    def test_reconcile_sorts_same_service_metric_ties(self):
        """Same-service actions with equal impact should sort by metric name."""
        work = APP / "tmp" / "m5_metric_tie"
        work.mkdir(parents=True, exist_ok=True)
        config_path = work / "rules.json"
        baseline_events = work / "baseline.jsonl"
        candidate_events = work / "candidate.jsonl"

        config_path.write_text(
            json.dumps(
                {
                    "version": 10,
                    "services": [
                        {
                            "name": "Search API",
                            "aliases": ["search"],
                            "tier": "critical",
                            "weight": 0.75,
                            "retention_days": 60,
                        }
                    ],
                }
            )
        )
        write_jsonl(
            baseline_events,
            [
                {
                    "event_id": "b-requests",
                    "service": "search",
                    "occurred_at": "2026-05-05T11:00:00Z",
                    "metric": "requests",
                    "value": 10,
                    "source": "edge-a",
                    "sequence": 1,
                    "kind": "measurement",
                }
            ],
        )
        write_jsonl(
            candidate_events,
            [
                {
                    "event_id": "c-requests",
                    "service": "Search API",
                    "occurred_at": "2026-05-06T11:00:00Z",
                    "metric": "requests",
                    "value": 10,
                    "source": "edge-a",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "c-errors",
                    "service": "search",
                    "occurred_at": "2026-05-06T11:01:00Z",
                    "metric": "errors",
                    "value": 2,
                    "source": "edge-b",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "c-cache-hits",
                    "service": "Search API",
                    "occurred_at": "2026-05-06T11:02:00Z",
                    "metric": "cache_hits",
                    "value": 2,
                    "source": "edge-cache",
                    "sequence": 1,
                    "kind": "measurement",
                },
            ],
        )

        port = free_port()
        proc = subprocess.Popen(
            ["go", "run", "./cmd/ledger", "serve", "--addr", f"127.0.0.1:{port}"],
            cwd=APP,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        try:
            base = f"http://127.0.0.1:{port}"
            deadline = time.time() + 30

            while time.time() < deadline:
                try:
                    status, _, health = request_json(f"{base}/health")
                    if status == 200 and health == {"ok": True}:
                        break
                except Exception:
                    time.sleep(0.25)
            else:
                raise AssertionError("server did not become healthy")

            report_url = f"{base}/v1/reports"
            _, _, baseline = request_json(
                report_url,
                {"config_path": str(config_path), "events_path": str(baseline_events)},
            )
            _, _, candidate = request_json(
                report_url,
                {"config_path": str(config_path), "events_path": str(candidate_events)},
            )

            status, _, plan = request_json(
                f"{base}/v1/reports/reconcile",
                {
                    "baseline_report_id": baseline["report_id"],
                    "candidate_report_id": candidate["report_id"],
                },
            )
            assert status == 200
            assert plan["totals"] == {
                "action_count": 2,
                "total_impact_score": 8,
                "by_status": {"new_metric": 2},
                "by_tier": {"critical": 2},
            }
            assert [
                (action["service"], action["metric"], action["impact_score"])
                for action in plan["actions"]
            ] == [
                ("search-api", "cache_hits", 4),
                ("search-api", "errors", 4),
            ]
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    def test_reconcile_applies_custom_multipliers_and_suppression(self, weighted_reports):
        """Custom multipliers and suppressed statuses should shape ranked actions."""
        status, headers, plan = request_reconcile(
            weighted_reports,
            min_abs_delta=2,
            tier_multipliers={"critical": 3, "standard": 0.5},
            suppress_statuses=["removed_metric"],
        )
        assert status == 200
        assert headers.get_content_type() == "application/json"
        assert plan["baseline_report_id"] == weighted_reports["baseline_report_id"]
        assert plan["candidate_report_id"] == weighted_reports["candidate_report_id"]
        assert plan["min_abs_delta"] == 2
        assert plan["suppressed_statuses"] == ["removed_metric"]
        assert plan["totals"] == {
            "action_count": 5,
            "total_impact_score": 196,
            "by_status": {"improved": 1, "new_metric": 1, "regressed": 3},
            "by_tier": {"critical": 2, "standard": 3},
        }
        assert plan["actions"] == [
            {
                "service": "search-api",
                "tier": "critical",
                "metric": "latency_ms",
                "status": "regressed",
                "delta_sum": 60,
                "absolute_delta": 60,
                "impact_score": 180,
                "recommendation": "investigate_candidate",
            },
            {
                "service": "search-api",
                "tier": "critical",
                "metric": "cache_hits",
                "status": "new_metric",
                "delta_sum": 3,
                "absolute_delta": 3,
                "impact_score": 9,
                "recommendation": "investigate_candidate",
            },
            {
                "service": "data-worker",
                "tier": "standard",
                "metric": "jobs",
                "status": "improved",
                "delta_sum": -6,
                "absolute_delta": 6,
                "impact_score": 3,
                "recommendation": "verify_reduction",
            },
            {
                "service": "alpha-api",
                "tier": "standard",
                "metric": "backlog",
                "status": "regressed",
                "delta_sum": 4,
                "absolute_delta": 4,
                "impact_score": 2,
                "recommendation": "investigate_candidate",
            },
            {
                "service": "billing-api",
                "tier": "standard",
                "metric": "invoices",
                "status": "regressed",
                "delta_sum": 4,
                "absolute_delta": 4,
                "impact_score": 2,
                "recommendation": "investigate_candidate",
            },
        ]

    def test_reconcile_uses_default_inputs_without_budget_plan(self, weighted_reports):
        """Omitted optional inputs should use defaults and omit budget_plan."""
        status, _, default_plan = request_reconcile(weighted_reports)
        assert status == 200
        assert default_plan["min_abs_delta"] == 0
        assert default_plan["suppressed_statuses"] == []
        assert "budget_plan" not in default_plan
        assert default_plan["totals"] == {
            "action_count": 6,
            "total_impact_score": 144,
            "by_status": {
                "improved": 1,
                "new_metric": 1,
                "regressed": 3,
                "removed_metric": 1,
            },
            "by_tier": {"critical": 3, "standard": 3},
        }
        assert default_plan["actions"] == [
            {
                "service": "search-api",
                "tier": "critical",
                "metric": "latency_ms",
                "status": "regressed",
                "delta_sum": 60,
                "absolute_delta": 60,
                "impact_score": 120,
                "recommendation": "investigate_candidate",
            },
            {
                "service": "data-worker",
                "tier": "standard",
                "metric": "jobs",
                "status": "improved",
                "delta_sum": -6,
                "absolute_delta": 6,
                "impact_score": 6,
                "recommendation": "verify_reduction",
            },
            {
                "service": "search-api",
                "tier": "critical",
                "metric": "cache_hits",
                "status": "new_metric",
                "delta_sum": 3,
                "absolute_delta": 3,
                "impact_score": 6,
                "recommendation": "investigate_candidate",
            },
            {
                "service": "alpha-api",
                "tier": "standard",
                "metric": "backlog",
                "status": "regressed",
                "delta_sum": 4,
                "absolute_delta": 4,
                "impact_score": 4,
                "recommendation": "investigate_candidate",
            },
            {
                "service": "billing-api",
                "tier": "standard",
                "metric": "invoices",
                "status": "regressed",
                "delta_sum": 4,
                "absolute_delta": 4,
                "impact_score": 4,
                "recommendation": "investigate_candidate",
            },
            {
                "service": "search-api",
                "tier": "critical",
                "metric": "errors",
                "status": "removed_metric",
                "delta_sum": -2,
                "absolute_delta": 2,
                "impact_score": 4,
                "recommendation": "verify_reduction",
            },
        ]

    def test_reconcile_rounds_fractional_impacts_before_budgeting(self, weighted_reports):
        """Fractional multipliers should round before sorting, totals, and caps."""
        status, _, rounded_plan = request_reconcile(
            weighted_reports,
            tier_multipliers={"critical": 0.333, "standard": 0.335},
            impact_budget={"max_total_impact": 3.35},
        )
        assert status == 200
        assert rounded_plan["totals"]["total_impact_score"] == 26.34
        assert [
            (action["service"], action["metric"], action["impact_score"])
            for action in rounded_plan["actions"]
        ] == [
            ("search-api", "latency_ms", 19.98),
            ("data-worker", "jobs", 2.01),
            ("alpha-api", "backlog", 1.34),
            ("billing-api", "invoices", 1.34),
            ("search-api", "cache_hits", 1),
            ("search-api", "errors", 0.67),
        ]
        assert rounded_plan["budget_plan"]["totals"] == {
            "selected_count": 2,
            "deferred_count": 4,
            "selected_impact_score": 3.35,
            "deferred_impact_score": 22.99,
            "selected_by_tier": {"standard": 2},
            "deferred_by_tier": {"critical": 3, "standard": 1},
            "selected_by_service": {"alpha-api": 1, "data-worker": 1},
            "deferred_by_service": {"billing-api": 1, "search-api": 3},
        }
        assert [
            (action["service"], action["metric"], action["impact_score"])
            for action in rounded_plan["budget_plan"]["selected_actions"]
        ] == [
            ("data-worker", "jobs", 2.01),
            ("alpha-api", "backlog", 1.34),
        ]
        assert rounded_plan["budget_plan"]["deferred_reasons"] == [
            {"service": "search-api", "metric": "latency_ms", "reasons": ["max_total_impact"]},
            {"service": "billing-api", "metric": "invoices", "reasons": ["max_total_impact"]},
            {"service": "search-api", "metric": "cache_hits", "reasons": ["max_total_impact"]},
            {"service": "search-api", "metric": "errors", "reasons": ["max_total_impact"]},
        ]

    def test_reconcile_budget_plan_keeps_scanning_after_deferrals(self, weighted_reports):
        """Budget planning should scan greedily and keep later fitting actions."""
        _, _, default_plan = request_reconcile(weighted_reports)
        status, _, budgeted_plan = request_reconcile(
            weighted_reports,
            impact_budget={
                "max_total_impact": 16,
                "tier_limits": {"critical": 10, "standard": 10},
            },
        )
        assert status == 200
        assert budgeted_plan["totals"] == default_plan["totals"]
        assert budgeted_plan["actions"] == default_plan["actions"]
        assert budgeted_plan["budget_plan"]["max_total_impact"] == 16
        assert budgeted_plan["budget_plan"]["tier_limits"] == {
            "critical": 10,
            "standard": 10,
        }
        assert budgeted_plan["budget_plan"]["totals"] == {
            "selected_count": 3,
            "deferred_count": 3,
            "selected_impact_score": 16,
            "deferred_impact_score": 128,
            "selected_by_tier": {"critical": 1, "standard": 2},
            "deferred_by_tier": {"critical": 2, "standard": 1},
            "selected_by_service": {
                "alpha-api": 1,
                "data-worker": 1,
                "search-api": 1,
            },
            "deferred_by_service": {"billing-api": 1, "search-api": 2},
        }
        assert budgeted_plan["budget_plan"]["service_limits"] == {}
        assert budgeted_plan["budget_plan"]["status_limits"] == {}
        assert [
            (action["service"], action["metric"], action["impact_score"])
            for action in budgeted_plan["budget_plan"]["selected_actions"]
        ] == [
            ("data-worker", "jobs", 6),
            ("search-api", "cache_hits", 6),
            ("alpha-api", "backlog", 4),
        ]
        assert [
            (action["service"], action["metric"], action["impact_score"])
            for action in budgeted_plan["budget_plan"]["deferred_actions"]
        ] == [
            ("search-api", "latency_ms", 120),
            ("billing-api", "invoices", 4),
            ("search-api", "errors", 4),
        ]
        assert budgeted_plan["budget_plan"]["deferred_reasons"] == [
            {
                "service": "search-api",
                "metric": "latency_ms",
                "reasons": ["max_total_impact", "tier_limit"],
            },
            {
                "service": "billing-api",
                "metric": "invoices",
                "reasons": ["max_total_impact", "tier_limit"],
            },
            {"service": "search-api", "metric": "errors", "reasons": ["max_total_impact"]},
        ]

    def test_reconcile_allows_tier_only_budgets(self, weighted_reports):
        """Tier-only budgets should work without a max_total_impact cap."""
        status, _, tier_only_budget = request_reconcile(
            weighted_reports,
            impact_budget={"tier_limits": {"critical": 8}},
        )
        assert status == 200
        assert "max_total_impact" not in tier_only_budget["budget_plan"]
        assert tier_only_budget["budget_plan"]["tier_limits"] == {"critical": 8}
        assert tier_only_budget["budget_plan"]["service_limits"] == {}
        assert tier_only_budget["budget_plan"]["status_limits"] == {}
        assert [
            (action["service"], action["metric"], action["impact_score"])
            for action in tier_only_budget["budget_plan"]["selected_actions"]
        ] == [
            ("data-worker", "jobs", 6),
            ("search-api", "cache_hits", 6),
            ("alpha-api", "backlog", 4),
            ("billing-api", "invoices", 4),
        ]
        assert [
            (action["service"], action["metric"], action["impact_score"])
            for action in tier_only_budget["budget_plan"]["deferred_actions"]
        ] == [
            ("search-api", "latency_ms", 120),
            ("search-api", "errors", 4),
        ]
        assert tier_only_budget["budget_plan"]["deferred_reasons"] == [
            {"service": "search-api", "metric": "latency_ms", "reasons": ["tier_limit"]},
            {"service": "search-api", "metric": "errors", "reasons": ["tier_limit"]},
        ]

    def test_reconcile_echoes_zero_and_unused_budget_limits(self, weighted_reports):
        """Zero and unused caps should be echoed without zero-count breakdown keys."""
        status, _, zero_budget = request_reconcile(
            weighted_reports,
            impact_budget={
                "tier_limits": {"critical": 0, "experimental": 0},
                "service_limits": {"Billing API": 0, "No Such Service": 0},
                "status_limits": {"new_metric": 99, "removed_metric": 0},
            },
        )
        assert status == 200
        assert zero_budget["budget_plan"]["tier_limits"] == {
            "critical": 0,
            "experimental": 0,
        }
        assert zero_budget["budget_plan"]["service_limits"] == {
            "billing-api": 0,
            "no-such-service": 0,
        }
        assert zero_budget["budget_plan"]["status_limits"] == {
            "new_metric": 99,
            "removed_metric": 0,
        }
        assert zero_budget["budget_plan"]["totals"] == {
            "selected_count": 2,
            "deferred_count": 4,
            "selected_impact_score": 10,
            "deferred_impact_score": 134,
            "selected_by_tier": {"standard": 2},
            "deferred_by_tier": {"critical": 3, "standard": 1},
            "selected_by_service": {"alpha-api": 1, "data-worker": 1},
            "deferred_by_service": {"billing-api": 1, "search-api": 3},
        }
        assert [
            (action["service"], action["metric"], action["impact_score"])
            for action in zero_budget["budget_plan"]["selected_actions"]
        ] == [("data-worker", "jobs", 6), ("alpha-api", "backlog", 4)]
        assert zero_budget["budget_plan"]["deferred_reasons"] == [
            {"service": "search-api", "metric": "latency_ms", "reasons": ["tier_limit"]},
            {"service": "search-api", "metric": "cache_hits", "reasons": ["tier_limit"]},
            {"service": "billing-api", "metric": "invoices", "reasons": ["service_limit"]},
            {
                "service": "search-api",
                "metric": "errors",
                "reasons": ["tier_limit", "status_limit"],
            },
        ]

    def test_reconcile_enforces_normalized_service_limits(self, weighted_reports):
        """Service limits should normalize keys and produce service_limit reasons."""
        status, _, service_budget = request_reconcile(
            weighted_reports,
            impact_budget={
                "max_total_impact": 14,
                "service_limits": {
                    "Search API": 8,
                    "Data Worker": 7,
                    "Alpha API": 4,
                },
            },
        )
        assert status == 200
        assert service_budget["budget_plan"]["max_total_impact"] == 14
        assert service_budget["budget_plan"]["tier_limits"] == {}
        assert service_budget["budget_plan"]["service_limits"] == {
            "alpha-api": 4,
            "data-worker": 7,
            "search-api": 8,
        }
        assert service_budget["budget_plan"]["status_limits"] == {}
        assert service_budget["budget_plan"]["totals"] == {
            "selected_count": 2,
            "deferred_count": 4,
            "selected_impact_score": 12,
            "deferred_impact_score": 132,
            "selected_by_tier": {"critical": 1, "standard": 1},
            "deferred_by_tier": {"critical": 2, "standard": 2},
            "selected_by_service": {"data-worker": 1, "search-api": 1},
            "deferred_by_service": {
                "alpha-api": 1,
                "billing-api": 1,
                "search-api": 2,
            },
        }
        assert [
            (action["service"], action["metric"], action["impact_score"])
            for action in service_budget["budget_plan"]["selected_actions"]
        ] == [("data-worker", "jobs", 6), ("search-api", "cache_hits", 6)]
        assert service_budget["budget_plan"]["deferred_reasons"] == [
            {
                "service": "search-api",
                "metric": "latency_ms",
                "reasons": ["max_total_impact", "service_limit"],
            },
            {"service": "alpha-api", "metric": "backlog", "reasons": ["max_total_impact"]},
            {"service": "billing-api", "metric": "invoices", "reasons": ["max_total_impact"]},
            {
                "service": "search-api",
                "metric": "errors",
                "reasons": ["max_total_impact", "service_limit"],
            },
        ]

    def test_reconcile_enforces_status_limits(self, weighted_reports):
        """Status limits should cap cumulative impact by change class."""
        status, _, status_budget = request_reconcile(
            weighted_reports,
            impact_budget={
                "status_limits": {
                    "regressed": 10,
                    "new_metric": 10,
                    "improved": 10,
                    "removed_metric": 10,
                },
            },
        )
        assert status == 200
        assert "max_total_impact" not in status_budget["budget_plan"]
        assert status_budget["budget_plan"]["tier_limits"] == {}
        assert status_budget["budget_plan"]["service_limits"] == {}
        assert status_budget["budget_plan"]["status_limits"] == {
            "improved": 10,
            "new_metric": 10,
            "regressed": 10,
            "removed_metric": 10,
        }
        assert status_budget["budget_plan"]["totals"] == {
            "selected_count": 5,
            "deferred_count": 1,
            "selected_impact_score": 24,
            "deferred_impact_score": 120,
            "selected_by_tier": {"critical": 2, "standard": 3},
            "deferred_by_tier": {"critical": 1},
            "selected_by_service": {
                "alpha-api": 1,
                "billing-api": 1,
                "data-worker": 1,
                "search-api": 2,
            },
            "deferred_by_service": {"search-api": 1},
        }
        assert [
            (action["service"], action["metric"], action["status"], action["impact_score"])
            for action in status_budget["budget_plan"]["selected_actions"]
        ] == [
            ("data-worker", "jobs", "improved", 6),
            ("search-api", "cache_hits", "new_metric", 6),
            ("alpha-api", "backlog", "regressed", 4),
            ("billing-api", "invoices", "regressed", 4),
            ("search-api", "errors", "removed_metric", 4),
        ]
        assert [
            (action["service"], action["metric"], action["status"], action["impact_score"])
            for action in status_budget["budget_plan"]["deferred_actions"]
        ] == [("search-api", "latency_ms", "regressed", 120)]
        assert status_budget["budget_plan"]["deferred_reasons"] == [
            {"service": "search-api", "metric": "latency_ms", "reasons": ["status_limit"]}
        ]

    def test_reconcile_suppresses_multiple_statuses_and_keeps_compare(self, weighted_reports):
        """Multiple suppressed statuses should not break compare behavior."""
        status, _, suppressed_plan = request_reconcile(
            weighted_reports,
            suppress_statuses=["regressed", "improved", "new_metric"],
        )
        assert status == 200
        assert suppressed_plan["suppressed_statuses"] == [
            "improved",
            "new_metric",
            "regressed",
        ]
        assert suppressed_plan["totals"] == {
            "action_count": 1,
            "total_impact_score": 4,
            "by_status": {"removed_metric": 1},
            "by_tier": {"critical": 1},
        }
        assert suppressed_plan["actions"] == [
            {
                "service": "search-api",
                "tier": "critical",
                "metric": "errors",
                "status": "removed_metric",
                "delta_sum": -2,
                "absolute_delta": 2,
                "impact_score": 4,
                "recommendation": "verify_reduction",
            }
        ]

        status, _, comparison = request_json(
            f"{weighted_reports['base']}/v1/reports/compare",
            {
                "baseline_report_id": weighted_reports["baseline_report_id"],
                "candidate_report_id": weighted_reports["candidate_report_id"],
                "min_abs_delta": 2,
            },
        )
        assert status == 200
        assert comparison["totals"]["removed_metrics"] == 1

    def test_reconcile_rejects_invalid_requests(self, weighted_reports):
        """Invalid reconcile request shapes and values should return 400 or 404."""
        url = f"{weighted_reports['base']}/v1/reports/reconcile"
        base_ids = {
            "baseline_report_id": weighted_reports["baseline_report_id"],
            "candidate_report_id": weighted_reports["candidate_report_id"],
        }

        assert_http_error(url, 400, raw_data=b"not valid json{{{")
        assert_http_error(url, 400, {"candidate_report_id": base_ids["candidate_report_id"]})
        assert_http_error(url, 400, {"baseline_report_id": base_ids["baseline_report_id"]})
        assert_http_error(url, 400, base_ids | {"min_abs_delta": -1})
        assert_http_error(url, 400, base_ids | {"tier_multipliers": {"critical": 0}})
        assert_http_error(url, 400, base_ids | {"suppress_statuses": ["unknown_status"]})
        assert_http_error(url, 400, base_ids | {"impact_budget": {"max_total_impact": -0.01}})
        assert_http_error(url, 400, base_ids | {"impact_budget": {"tier_limits": {"critical": -1}}})
        assert_http_error(url, 400, base_ids | {"impact_budget": {"service_limits": {"search-api": -1}}})
        assert_http_error(url, 400, base_ids | {"impact_budget": {"service_limits": {"!!!": 1}}})
        assert_http_error(url, 400, base_ids | {"impact_budget": {"status_limits": {"regressed": -1}}})
        assert_http_error(url, 400, base_ids | {"impact_budget": {"status_limits": {"unchanged": 1}}})
        assert_http_error(
            url,
            404,
            {
                "baseline_report_id": "missing-report",
                "candidate_report_id": base_ids["candidate_report_id"],
            },
        )
        assert_http_error(
            url,
            404,
            {
                "baseline_report_id": base_ids["baseline_report_id"],
                "candidate_report_id": "missing-report",
            },
        )
