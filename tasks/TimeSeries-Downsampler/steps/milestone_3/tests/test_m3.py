"""Tests for Milestone 3: Causal Dependency Buffering."""
import os
import shutil
import subprocess
import tempfile

_MILESTONE = "m3"


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

class TestMilestone3:
    def test_events_without_dependencies_process_immediately(self):
        """Events with no dependencies are processed immediately."""
        assert "events_without_dependencies_process_immediately" in _PASSED

    def test_orphaned_event_is_buffered(self):
        """Events whose dependencies are unmet are held in the orphan buffer."""
        assert "orphaned_event_is_buffered" in _PASSED

    def test_recursive_unblocking_cascades_correctly(self):
        """A single event can recursively unblock a chain of dependent events."""
        assert "recursive_unblocking_cascades_correctly" in _PASSED

    def test_multiple_orphans_unblocked_by_one_event(self):
        """Multiple orphans waiting on the same dependency are unblocked together."""
        assert "multiple_orphans_unblocked_by_one_event" in _PASSED

    def test_cycle_is_detected_and_deadlettered(self):
        """Cyclic dependencies are detected and rejected to deadletter."""
        assert "cycle_is_detected_and_deadlettered" in _PASSED

    def test_deadletter_cascades_to_dependents(self):
        """Events depending on deadlettered items are also deadlettered."""
        assert "deadletter_cascades_to_dependents" in _PASSED

    def test_multi_parent_event_unblocks_only_when_all_met(self):
        """An event with multiple dependencies is only processed when ALL of them are met."""
        assert "multi_parent_event_unblocks_only_when_all_met" in _PASSED
