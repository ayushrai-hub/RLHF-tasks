"""Milestone 1 -- Decode Archive Schema.

The agent must complete the Polars migration harness so that
``python /app/harness/migrate.py schema --archive <dir> --out <dir>`` writes the
canonical schema report described in Appendix I of the chronicle. These tests
recompute the ground truth from the raw archive with an independent reference and
additionally drive the agent's harness against a disjoint synthetic archive, so a
hardcoded report cannot pass.

Run alone with: pytest /tests/test_m1.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
import relic_ref as R  # noqa: E402

ARCHIVE = "/app/archive"
REPORT = Path("/app/out/schema_report.json")


def _run_harness(command, archive, out):
    """Invoke the agent's harness; raise with captured output on failure."""
    proc = subprocess.run(
        [sys.executable, "/app/harness/migrate.py", command,
         "--archive", archive, "--out", out],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, (
        f"migrate.py {command} failed (rc={proc.returncode})\n"
        f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    )


class TestMilestone1:
    """Tests for milestone 1: the canonical archive schema report."""

    def test_report_exists(self) -> None:
        """The harness must write /app/out/schema_report.json."""
        assert REPORT.exists(), f"{REPORT} was not produced by the harness"

    def test_report_is_valid_json_object(self) -> None:
        """The report must be a JSON object keyed by the four source tables."""
        data = json.loads(REPORT.read_text(encoding="utf-8"))
        assert set(data.keys()) == {"monsters", "relics", "rooms", "tiles"}, (
            f"unexpected top-level keys: {sorted(data.keys())}"
        )

    def test_per_table_fields_and_fingerprints(self) -> None:
        """Each table entry must carry the columns, dtypes, row_count and the
        exact SHA-256 fingerprint mandated by Appendix I (Rule I.4)."""
        data = json.loads(REPORT.read_text(encoding="utf-8"))
        tables = R.read_archive(ARCHIVE)
        for name, rows in tables.items():
            expected = R.schema_entry(rows, R.PRIMARY_KEY[name])
            got = data[name]
            assert got["columns"] == expected["columns"], f"{name} columns"
            assert got["dtypes"] == expected["dtypes"], f"{name} dtypes"
            assert got["row_count"] == expected["row_count"], f"{name} row_count"
            assert got["fingerprint"] == expected["fingerprint"], (
                f"{name} fingerprint mismatch: {got['fingerprint']} "
                f"!= {expected['fingerprint']}"
            )

    def test_report_bytes_are_canonical(self) -> None:
        """The serialised report must be byte-for-byte canonical (sorted keys,
        two-space indent, single trailing newline)."""
        tables = R.read_archive(ARCHIVE)
        expected = R.schema_report_bytes(tables)
        assert REPORT.read_bytes() == expected, (
            "schema_report.json is not byte-identical to the canonical form"
        )

    def test_harness_on_synthetic_archive(self) -> None:
        """Driving the harness on a disjoint synthetic archive must yield the
        canonical report for THAT data -- proving the logic is data-driven and
        not a hardcoded copy of the shipped archive."""
        tables = R.synthetic_tables()
        expected = R.schema_report_bytes(tables)
        with tempfile.TemporaryDirectory() as tmp:
            arc = Path(tmp) / "archive"
            out = Path(tmp) / "out"
            arc.mkdir()
            R.write_archive(arc, tables)
            _run_harness("schema", str(arc), str(out))
            produced = (out / "schema_report.json").read_bytes()
        assert produced == expected, (
            "harness produced a non-canonical report on synthetic input"
        )
