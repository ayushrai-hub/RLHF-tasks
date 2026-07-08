"""Pytest helpers for milestone 3 Rails transparency API validation."""

import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from ledger_expected import CHAIN_ROOT, forged_rows, load_fixture_rows, receipt_id_for

REPORT = Path("/app/output/validation_report.json")
BASE = "http://127.0.0.1:9292"


def start_server():
    proc = subprocess.Popen(
        ["ruby", "/app/scripts/start_transparency_server.rb"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(40):
        try:
            with urllib.request.urlopen(f"{BASE}/ledger/root", timeout=1) as resp:
                if resp.status == 200:
                    return proc
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.25)
    proc.kill()
    raise RuntimeError("Rack server failed to start")


def http_json(method: str, path: str, payload=None):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())


class TestMilestone3:
    """Verify repaired Rack service and validation report."""

    def test_validation_report_and_api(self):
        """Report, receipt ids, validate endpoint, and root must match fixture truth."""
        assert REPORT.is_file(), "missing /app/output/validation_report.json"
        report = json.loads(REPORT.read_text())

        assert report["chain_root"] == CHAIN_ROOT
        expected_receipts = [
            {"seq": row[0], "receipt_id": receipt_id_for(row[0])}
            for row in load_fixture_rows()
        ]
        assert len(report["receipts"]) == len(expected_receipts)
        for actual, expected in zip(report["receipts"], expected_receipts):
            assert str(actual["seq"]) == expected["seq"]
            assert actual["receipt_id"] == expected["receipt_id"]

        forged_entries = report["forged_results"]
        assert isinstance(forged_entries, list) and len(forged_entries) >= 3
        valid_entries = [entry for entry in forged_entries if entry["valid"] is True]
        invalid_entries = [entry for entry in forged_entries if entry["valid"] is False]
        assert len(valid_entries) >= 1, "forged_results must include at least one accepted row"
        assert len(invalid_entries) >= 2, "forged_results must include at least two rejected rows"
        fixture_lines = {",".join(row) for row in load_fixture_rows()}
        assert any(entry["csv_row"] in fixture_lines for entry in valid_entries)

        proc = start_server()
        try:
            for entry in forged_entries:
                body = http_json("POST", "/ledger/validate", {"csv_row": entry["csv_row"]})
                assert body["valid"] == entry["valid"], entry["csv_row"]

            for row in load_fixture_rows():
                seq = row[0]
                body = http_json("GET", f"/receipts/{seq}")
                assert str(body["seq"]) == seq
                assert body["receipt_id"] == receipt_id_for(seq)

            for row in load_fixture_rows():
                body = http_json("POST", "/ledger/validate", {"csv_row": ",".join(row)})
                assert body["valid"] is True

            for csv_row, should_pass in forged_rows():
                if should_pass:
                    continue
                body = http_json("POST", "/ledger/validate", {"csv_row": csv_row})
                assert body["valid"] is False

            root_body = http_json("GET", "/ledger/root")
            assert root_body["root"] == CHAIN_ROOT
        finally:
            proc.terminate()
            proc.wait(timeout=5)
