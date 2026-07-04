"""Tests for Milestone 1: basic event parsing and tumbling window aggregation."""
import os
import shutil
import subprocess
import tempfile

_MILESTONE = "m1"


def _run_rust_verifier():
    """Run the milestone's Rust assertions from a verifier-owned cargo harness.

    The harness is created in a temporary directory outside /app and depends on
    the agent's crate via a path dependency, so no verifier files are ever
    written into the agent's workspace. Returns the set of passing test names.
    """
    test_rs = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), f"test_{_MILESTONE}.rs"
    )
    harness = tempfile.mkdtemp(prefix=f"verifier_{_MILESTONE}_")
    try:
        os.makedirs(os.path.join(harness, "src"), exist_ok=True)
        os.makedirs(os.path.join(harness, "tests"), exist_ok=True)
        with open(os.path.join(harness, "Cargo.toml"), "w") as fh:
            fh.write(
                "[package]\n"
                f'name = "verifier_{_MILESTONE}"\n'
                'version = "0.0.0"\n'
                'edition = "2021"\n\n'
                "[lib]\n"
                'path = "src/lib.rs"\n\n'
                "[dependencies]\n"
                'timeseries_downsampler = { path = "/app/app" }\n\n'
                "[[test]]\n"
                f'name = "test_{_MILESTONE}"\n'
                f'path = "tests/test_{_MILESTONE}.rs"\n'
            )
        open(os.path.join(harness, "src", "lib.rs"), "w").close()
        shutil.copyfile(
            test_rs, os.path.join(harness, "tests", f"test_{_MILESTONE}.rs")
        )
        result = subprocess.run(
            ["cargo", "test",
             "--manifest-path", os.path.join(harness, "Cargo.toml"),
             "--test", f"test_{_MILESTONE}", "--offline",
             "--", "--test-threads=1"],
            capture_output=True, text=True, timeout=300,
        )
        output = result.stdout + result.stderr
        passed = set()
        for line in output.splitlines():
            line = line.strip()
            parts = line.split(" ... ")
            if line.startswith("test ") and len(parts) == 2 and parts[1].strip() == "ok":
                passed.add(parts[0][5:])
        return passed
    except Exception:
        return set()
    finally:
        shutil.rmtree(harness, ignore_errors=True)


_PASSED = _run_rust_verifier()

class TestMilestone1:
    def test_parse_valid_event(self):
        """Valid pipe-delimited strings are parsed into Event structs correctly."""
        assert "parse_valid_event" in _PASSED

    def test_parse_b64_event(self):
        """Base64 encoded IEEE 754 double precision floats are parsed correctly."""
        assert "parse_b64_event" in _PASSED

    def test_parse_valid_event_with_quotes(self):
        """Metrics with quoted names are parsed correctly, ignoring embedded pipes."""
        assert "parse_valid_event_with_quotes" in _PASSED

    def test_parse_invalid_events_returns_none(self):
        """Blank lines or lines with invalid data return None."""
        assert "parse_invalid_events_returns_none" in _PASSED

    def test_tumbling_window_calculates_correct_bounds(self):
        """Tumbling window aggregator groups events into correct time boundaries."""
        assert "tumbling_window_calculates_correct_bounds" in _PASSED

    def test_tumbling_window_aggregates_stats(self):
        """Tumbling window correctly calculates min, max, avg, count, and median."""
        assert "tumbling_window_aggregates_stats" in _PASSED

    def test_flush_window_removes_data(self):
        """Flushing a window returns its results and clears it from the aggregator's memory."""
        assert "flush_window_removes_data" in _PASSED
