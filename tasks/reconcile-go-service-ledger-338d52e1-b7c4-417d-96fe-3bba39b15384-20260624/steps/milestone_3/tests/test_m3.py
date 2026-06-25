"""Verifier for milestone 3 HTTP report API behavior."""

import csv
import hashlib
import json
import re
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


class TestMilestone3:
    def test_report_api_creates_stable_json_and_csv_reports(self):
        """The HTTP API should create stable reports and serve sorted CSV exports."""
        work = APP / "tmp" / "m3"
        work.mkdir(parents=True, exist_ok=True)
        config_path = work / "rules.json"
        events_path = work / "events.jsonl"

        # Arrange source data that requires alias rollup and sorted CSV output.
        config_path.write_text(
            json.dumps(
                {
                    "version": 8,
                    "services": [
                        {
                            "name": "Search API",
                            "aliases": ["search", "lookup"],
                            "tier": "critical",
                            "weight": 0.75,
                            "retention_days": 60,
                        },
                        {
                            "name": "Data Worker",
                            "aliases": ["worker"],
                            "tier": "standard",
                            "weight": 0.35,
                            "retention_days": 20,
                        },
                    ],
                }
            )
        )
        write_jsonl(
            events_path,
            [
                {
                    "event_id": "s-1",
                    "service": "lookup",
                    "occurred_at": "2026-05-02T11:00:00Z",
                    "metric": "latency_ms",
                    "value": 50,
                    "source": "edge-a",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "s-2",
                    "service": "Search API",
                    "occurred_at": "2026-05-02T11:01:00Z",
                    "metric": "latency_ms",
                    "value": 71,
                    "source": "edge-b",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "s-3",
                    "service": "search",
                    "occurred_at": "2026-05-02T11:01:30Z",
                    "metric": "errors",
                    "value": 3,
                    "source": "edge-a",
                    "sequence": 1,
                    "kind": "measurement",
                },
                {
                    "event_id": "w-1",
                    "service": "worker",
                    "occurred_at": "2026-05-02T11:02:00Z",
                    "metric": "jobs",
                    "value": 4,
                    "source": "batch",
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

            # Wait for the server and verify the health payload has exactly the documented shape.
            while time.time() < deadline:
                try:
                    status, _, health = request_json(f"{base}/health")
                    if status == 200 and health == {"ok": True}:
                        break
                except Exception:
                    time.sleep(0.25)
            else:
                raise AssertionError("server did not become healthy")

            # Create a report and verify the stable id is derived from the returned canonical summary.
            body = {"config_path": str(config_path), "events_path": str(events_path)}
            status, headers, first = request_json(f"{base}/v1/reports", body)
            assert status == 201
            assert headers.get_content_type() == "application/json"
            assert re.fullmatch(r"[0-9a-f]{16}", first["report_id"])
            expected_id = hashlib.sha256(
                json.dumps(first["summary"], separators=(",", ":")).encode()
            ).hexdigest()[:16]
            assert first["report_id"] == expected_id
            assert first["summary"]["totals"] == {
                "service_count": 2,
                "event_count": 4,
                "dropped_events": 0,
                "suppressed_events": 0,
            }
            assert first["summary"]["services"] == [
                {
                    "service": "data-worker",
                    "tier": "standard",
                    "event_count": 1,
                    "sources": ["batch"],
                    "metrics": {
                        "jobs": {"count": 1, "sum": 4, "min": 4, "max": 4, "avg": 4}
                    },
                },
                {
                    "service": "search-api",
                    "tier": "critical",
                    "event_count": 3,
                    "sources": ["edge-a", "edge-b"],
                    "metrics": {
                        "errors": {
                            "count": 1,
                            "sum": 3,
                            "min": 3,
                            "max": 3,
                            "avg": 3,
                        },
                        "latency_ms": {
                            "count": 2,
                            "sum": 121,
                            "min": 50,
                            "max": 71,
                            "avg": 60.5,
                        },
                    },
                },
            ]

            status, _, second = request_json(f"{base}/v1/reports", body)
            assert status == 201
            assert second["report_id"] == first["report_id"]

            # Retrieve the CSV export and verify column order, row order, and serialized values.
            with urllib.request.urlopen(
                f"{base}/v1/reports/{first['report_id']}.csv", timeout=5
            ) as response:
                assert response.status == 200
                assert response.headers.get_content_type() == "text/csv"
                rows = list(csv.DictReader(response.read().decode().splitlines()))

            assert rows
            assert list(rows[0].keys()) == [
                "service",
                "tier",
                "metric",
                "count",
                "sum",
                "min",
                "max",
                "avg",
                "sources",
            ]
            assert [(row["service"], row["metric"]) for row in rows] == [
                ("data-worker", "jobs"),
                ("search-api", "errors"),
                ("search-api", "latency_ms"),
            ]
            assert rows[0]["metric"] == "jobs"
            assert rows[0]["tier"] == "standard"
            assert rows[0]["min"] == "4"
            assert rows[0]["max"] == "4"
            assert rows[0]["sources"] == "batch"
            assert rows[1]["tier"] == "critical"
            assert rows[1]["count"] == "1"
            assert rows[1]["sum"] == "3"
            assert rows[1]["min"] == "3"
            assert rows[1]["max"] == "3"
            assert rows[1]["avg"] == "3"
            assert rows[2]["metric"] == "latency_ms"
            assert rows[2]["tier"] == "critical"
            assert rows[2]["count"] == "2"
            assert rows[2]["sum"] == "121"
            assert rows[2]["min"] == "50"
            assert rows[2]["max"] == "71"
            assert rows[2]["avg"] == "60.5"
            assert rows[2]["sources"] == "edge-a;edge-b"

            # Verify request validation and missing-report errors.
            try:
                request_json(f"{base}/v1/reports", {"config_path": str(config_path)})
                raise AssertionError("missing events_path did not return 400")
            except urllib.error.HTTPError as exc:
                assert exc.code == 400

            try:
                request_json(f"{base}/v1/reports", {"events_path": str(events_path)})
                raise AssertionError("missing config_path did not return 400")
            except urllib.error.HTTPError as exc:
                assert exc.code == 400

            bad_req = urllib.request.Request(
                f"{base}/v1/reports",
                data=b"not json",
                headers={"Content-Type": "application/json"},
            )
            try:
                urllib.request.urlopen(bad_req, timeout=5)
                raise AssertionError("invalid JSON did not return 400")
            except urllib.error.HTTPError as exc:
                assert exc.code == 400

            try:
                urllib.request.urlopen(f"{base}/v1/reports/missing.csv", timeout=5)
                raise AssertionError("unknown report id did not return 404")
            except urllib.error.HTTPError as exc:
                assert exc.code == 404
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
