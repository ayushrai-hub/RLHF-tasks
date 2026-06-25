"""Verifier for milestone 4 report comparison behavior."""

import json
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


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


class TestMilestone4:
    def test_compare_reports_classifies_metric_drift_and_errors(self):
        """Report comparison should classify sorted metric changes and reject bad requests."""
        work = APP / "tmp" / "m4"
        work.mkdir(parents=True, exist_ok=True)
        config_path = work / "rules.json"
        baseline_events = work / "baseline.jsonl"
        candidate_events = work / "candidate.jsonl"

        # Arrange shared service rules for two report snapshots.
        config_path.write_text(
            json.dumps(
                {
                    "version": 9,
                    "services": [
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

        # Arrange the baseline with a metric that will later regress, improve, disappear, or stay below threshold.
        write_jsonl(
            baseline_events,
            [
                {
                    "event_id": "b-latency",
                    "service": "lookup",
                    "occurred_at": "2026-05-03T11:00:00Z",
                    "metric": "latency_ms",
                    "value": 100,
                    "source": "edge-a",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "b-errors",
                    "service": "Search API",
                    "occurred_at": "2026-05-03T11:01:00Z",
                    "metric": "errors",
                    "value": 2,
                    "source": "edge-a",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "b-jobs",
                    "service": "worker",
                    "occurred_at": "2026-05-03T11:02:00Z",
                    "metric": "jobs",
                    "value": 10,
                    "source": "batch",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "b-invoices",
                    "service": "billing",
                    "occurred_at": "2026-05-03T11:03:00Z",
                    "metric": "invoices",
                    "value": 25,
                    "source": "core",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "b-boundary",
                    "service": "billing",
                    "occurred_at": "2026-05-03T11:04:00Z",
                    "metric": "boundary_drift",
                    "value": 10,
                    "source": "core",
                    "sequence": 1,
                    "kind": "measurement",
                },
            ],
        )

        # Arrange the candidate with one new metric, one removed metric, one regression, one improvement,
        # and one metric exactly at the threshold boundary.
        write_jsonl(
            candidate_events,
            [
                {
                    "event_id": "c-latency",
                    "service": "search",
                    "occurred_at": "2026-05-04T11:00:00Z",
                    "metric": "latency_ms",
                    "value": 160,
                    "source": "edge-b",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "c-cache",
                    "service": "Search API",
                    "occurred_at": "2026-05-04T11:01:00Z",
                    "metric": "cache_hits",
                    "value": 3,
                    "source": "edge-cache",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "c-jobs",
                    "service": "worker",
                    "occurred_at": "2026-05-04T11:02:00Z",
                    "metric": "jobs",
                    "value": 4,
                    "source": "ops",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "c-invoices",
                    "service": "billing",
                    "occurred_at": "2026-05-04T11:03:00Z",
                    "metric": "invoices",
                    "value": 29,
                    "source": "core",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "c-boundary",
                    "service": "billing",
                    "occurred_at": "2026-05-04T11:04:00Z",
                    "metric": "boundary_drift",
                    "value": 15,
                    "source": "core",
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

            # Wait for the API and keep the exact health-contract assertion from milestone 3.
            while time.time() < deadline:
                try:
                    status, _, health = request_json(f"{base}/health")
                    if status == 200 and health == {"ok": True}:
                        break
                except Exception:
                    time.sleep(0.25)
            else:
                raise AssertionError("server did not become healthy")

            # Create both reports in memory so compare must operate on stored summaries by id.
            report_url = f"{base}/v1/reports"
            _, _, baseline = request_json(
                report_url,
                {"config_path": str(config_path), "events_path": str(baseline_events)},
            )
            _, _, candidate = request_json(
                report_url,
                {"config_path": str(config_path), "events_path": str(candidate_events)},
            )

            # Compare the report ids and verify sorted drift classifications and totals.
            status, headers, comparison = request_json(
                f"{base}/v1/reports/compare",
                {
                    "baseline_report_id": baseline["report_id"],
                    "candidate_report_id": candidate["report_id"],
                    "min_abs_delta": 5,
                },
            )
            assert status == 200
            assert headers.get_content_type() == "application/json"
            assert comparison["baseline_report_id"] == baseline["report_id"]
            assert comparison["candidate_report_id"] == candidate["report_id"]
            assert comparison["min_abs_delta"] == 5
            assert comparison["totals"] == {
                "changed_metrics": 4,
                "new_metrics": 1,
                "removed_metrics": 1,
                "regressed_metrics": 1,
                "improved_metrics": 1,
            }
            assert comparison["changes"] == [
                {
                    "service": "data-worker",
                    "metric": "jobs",
                    "status": "improved",
                    "baseline_count": 1,
                    "candidate_count": 1,
                    "baseline_sum": 10,
                    "candidate_sum": 4,
                    "delta_sum": -6,
                    "percent_change": -60,
                },
                {
                    "service": "search-api",
                    "metric": "cache_hits",
                    "status": "new_metric",
                    "baseline_count": 0,
                    "candidate_count": 1,
                    "baseline_sum": 0,
                    "candidate_sum": 3,
                    "delta_sum": 3,
                    "percent_change": None,
                },
                {
                    "service": "search-api",
                    "metric": "errors",
                    "status": "removed_metric",
                    "baseline_count": 1,
                    "candidate_count": 0,
                    "baseline_sum": 2,
                    "candidate_sum": 0,
                    "delta_sum": -2,
                    "percent_change": -100,
                },
                {
                    "service": "search-api",
                    "metric": "latency_ms",
                    "status": "regressed",
                    "baseline_count": 1,
                    "candidate_count": 1,
                    "baseline_sum": 100,
                    "candidate_sum": 160,
                    "delta_sum": 60,
                    "percent_change": 60,
                },
            ]
            assert not any(
                change["service"] == "billing-api" and change["metric"] == "boundary_drift"
                for change in comparison["changes"]
            )

            # Omitting min_abs_delta should default to 0 and include smaller and boundary drifts.
            status, _, default_comparison = request_json(
                f"{base}/v1/reports/compare",
                {
                    "baseline_report_id": baseline["report_id"],
                    "candidate_report_id": candidate["report_id"],
                },
            )
            assert status == 200
            assert default_comparison["min_abs_delta"] == 0
            assert default_comparison["totals"] == {
                "changed_metrics": 6,
                "new_metrics": 1,
                "removed_metrics": 1,
                "regressed_metrics": 3,
                "improved_metrics": 1,
            }
            assert len(default_comparison["changes"]) == 6
            assert {
                "service": "billing-api",
                "metric": "boundary_drift",
                "status": "regressed",
                "baseline_count": 1,
                "candidate_count": 1,
                "baseline_sum": 10,
                "candidate_sum": 15,
                "delta_sum": 5,
                "percent_change": 50,
            } in default_comparison["changes"]
            assert {
                "service": "billing-api",
                "metric": "invoices",
                "status": "regressed",
                "baseline_count": 1,
                "candidate_count": 1,
                "baseline_sum": 25,
                "candidate_sum": 29,
                "delta_sum": 4,
                "percent_change": 16,
            } in default_comparison["changes"]

            # Verify compare endpoint validation and missing-id handling.
            malformed_req = urllib.request.Request(
                f"{base}/v1/reports/compare",
                data=b"not valid json{{{",
                headers={"Content-Type": "application/json"},
            )
            try:
                urllib.request.urlopen(malformed_req, timeout=5)
                raise AssertionError("malformed JSON did not return 400")
            except urllib.error.HTTPError as exc:
                assert exc.code == 400

            try:
                request_json(
                    f"{base}/v1/reports/compare",
                    {"baseline_report_id": baseline["report_id"], "min_abs_delta": 5},
                )
                raise AssertionError("missing candidate_report_id did not return 400")
            except urllib.error.HTTPError as exc:
                assert exc.code == 400

            try:
                request_json(
                    f"{base}/v1/reports/compare",
                    {"candidate_report_id": candidate["report_id"], "min_abs_delta": 5},
                )
                raise AssertionError("missing baseline_report_id did not return 400")
            except urllib.error.HTTPError as exc:
                assert exc.code == 400

            try:
                request_json(
                    f"{base}/v1/reports/compare",
                    {
                        "baseline_report_id": baseline["report_id"],
                        "candidate_report_id": candidate["report_id"],
                        "min_abs_delta": -1,
                    },
                )
                raise AssertionError("negative min_abs_delta did not return 400")
            except urllib.error.HTTPError as exc:
                assert exc.code == 400

            try:
                request_json(
                    f"{base}/v1/reports/compare",
                    {
                        "baseline_report_id": baseline["report_id"],
                        "candidate_report_id": "missing-report",
                    },
                )
                raise AssertionError("unknown candidate report id did not return 404")
            except urllib.error.HTTPError as exc:
                assert exc.code == 404

            try:
                request_json(
                    f"{base}/v1/reports/compare",
                    {
                        "baseline_report_id": "missing-report",
                        "candidate_report_id": candidate["report_id"],
                    },
                )
                raise AssertionError("unknown baseline report id did not return 404")
            except urllib.error.HTTPError as exc:
                assert exc.code == 404
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
