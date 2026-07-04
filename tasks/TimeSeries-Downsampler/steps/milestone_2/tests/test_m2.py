"""Tests for Milestone 2: overlapping sliding windows."""
import os
import shutil
import subprocess
import tempfile

_MILESTONE = "m2"


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

class TestMilestone2:
    def test_single_event_populates_multiple_windows(self):
        """A single event is added to all overlapping valid sliding windows."""
        assert "single_event_populates_multiple_windows" in _PASSED

    def test_sliding_window_boundaries_correct(self):
        """Events strictly inside the valid boundaries are included, while edges are correctly handled (start inclusive, end exclusive)."""
        assert "sliding_window_boundaries_correct" in _PASSED

    def test_multiple_events_aggregate_across_slides(self):
        """Multiple events aggregate correctly when their valid windows overlap."""
        assert "multiple_events_aggregate_across_slides" in _PASSED

    def test_duplicate_events_apply_bitwise_xor(self):
        """Duplicate events in the same window are aggregated using bitwise XOR of their IEEE 754 representations."""
        assert "duplicate_events_apply_bitwise_xor" in _PASSED

    def test_median_computation_even(self):
        """Median computation correctly averages the two middle elements when N is even."""
        assert "median_computation_even" in _PASSED
