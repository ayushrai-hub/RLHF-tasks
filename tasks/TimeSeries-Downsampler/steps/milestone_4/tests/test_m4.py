"""Tests for Milestone 4: Cascading Eviction."""
import os
import shutil
import subprocess
import tempfile

_MILESTONE = "m4"


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

class TestMilestone4:
    def test_evict_lowest_subtree_value(self):
        """Evicts the orphan with the lowest subtree value when over capacity."""
        assert "evict_lowest_subtree_value" in _PASSED

    def test_cascading_eviction_and_recalculation(self):
        """Evicting an event cascades, and capacity checking recalculates remaining subtree values."""
        assert "cascading_eviction_and_recalculation" in _PASSED

    def test_tie_breaking_by_event_id(self):
        """Ties in subtree value are broken by lexicographically smallest event_id."""
        assert "tie_breaking_by_event_id" in _PASSED

    def test_cascading_eviction_of_dependent_subtree(self):
        """Evicting an orphan must recursively evict its entire dependent subtree and clean up orphans map."""
        assert "cascading_eviction_of_dependent_subtree" in _PASSED

    def test_transitive_subtree_value_calculation(self):
        """Transitive dependencies must be correctly summed when calculating subtree values."""
        assert "transitive_subtree_value_calculation" in _PASSED

    def test_deduplication_in_return_value(self):
        """Evicted events returned should have exactly one instance even if they wait on multiple dependencies."""
        assert "deduplication_in_return_value" in _PASSED
