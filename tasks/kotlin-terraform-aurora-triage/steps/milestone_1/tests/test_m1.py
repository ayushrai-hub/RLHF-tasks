"""Unit tests for milestone 1. Validates protocol-decisions.json."""

import json
import subprocess
from pathlib import Path

DECISIONS_PATH = Path("/app/output/protocol-decisions.json")
EXTRACTOR_SRC = Path("/app/src/ProtocolExtractor.kt")


class TestMilestone1:
    """Tests for Milestone 1: Extract Protocol Decisions."""

    def test_milestone_1_files_exist(self) -> None:
        """Verify the source code file exists."""
        assert EXTRACTOR_SRC.is_file(), f"Source file {EXTRACTOR_SRC} does not exist"

    def test_milestone_1_base_execution(self) -> None:
        """Run the program and verify base decisions output values."""
        if DECISIONS_PATH.exists():
            DECISIONS_PATH.unlink()

        # Compile and execute
        compile_res = subprocess.run([
            "kotlinc", "-cp", "/usr/share/java/gson.jar",
            str(EXTRACTOR_SRC), "-include-runtime", "-d", "/tmp/ProtocolExtractor.jar"
        ], capture_output=True, text=True)
        assert compile_res.returncode == 0, f"Compilation failed: {compile_res.stderr}"

        run_res = subprocess.run([
            "java", "-cp", "/usr/share/java/gson.jar:/tmp/ProtocolExtractor.jar", "ProtocolExtractorKt"
        ], capture_output=True, text=True)
        assert run_res.returncode == 0, f"Execution failed: {run_res.stderr}"
        assert DECISIONS_PATH.exists(), f"Output file {DECISIONS_PATH} was not created"

        # Check values
        with open(DECISIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert abs(data["strong_aurora_threshold"] - 0.85) < 1e-5
        assert abs(data["quarantine_temp_threshold"] - (-25.0)) < 1e-5
        assert data["untrusted_sensor_id"] == "SNS-999"
        assert data["trusted_sensor_ids"] == ["SNS-001", "SNS-002", "SNS-003"]

    def test_milestone_1_mutated_execution(self) -> None:
        """Verify the program extracts decisions dynamically from mutated documentation."""
        orig_doc = Path("/app/docs/incident-archive.txt")
        backup_doc = Path("/tmp/incident-archive.txt.bak")
        orig_doc.rename(backup_doc)

        try:
            content = backup_doc.read_text(encoding="utf-8")
            stale_note = (
                "Legacy post-mortem note: sensor ID \"SNS-999\" was mentioned in "
                "the February 14 incident, but the approved rule lives in the "
                "February 18 meeting notes.\n"
            )

            mutated = stale_note + content.replace(
                "strong aurora probability threshold to\n  strictly 85% (0.85)",
                "strong aurora probability threshold to\n  strictly 92% (0.92)"
            ).replace(
                "strictly below -25C",
                "strictly below -18C"
            ).replace(
                'sensor ID "SNS-999"',
                'sensor ID "SNS-888"',
                1,
            ).replace(
                "Sensors SNS-001, SNS-002, and SNS-003",
                "Sensors SNS-101, SNS-102, and SNS-103",
                1,
            )

            with open(orig_doc, "w", encoding="utf-8") as f:
                f.write(mutated)

            if DECISIONS_PATH.exists():
                DECISIONS_PATH.unlink()

            # Execute
            run_res = subprocess.run([
                "java", "-cp", "/usr/share/java/gson.jar:/tmp/ProtocolExtractor.jar", "ProtocolExtractorKt"
            ], capture_output=True, text=True)
            assert run_res.returncode == 0, f"Execution failed on mutated doc: {run_res.stderr}"
            assert DECISIONS_PATH.exists(), "Output decisions file was not created on mutated doc"

            with open(DECISIONS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)

            assert abs(data["strong_aurora_threshold"] - 0.92) < 1e-5
            assert abs(data["quarantine_temp_threshold"] - (-18.0)) < 1e-5
            assert data["untrusted_sensor_id"] == "SNS-888"
            assert data["trusted_sensor_ids"] == ["SNS-101", "SNS-102", "SNS-103"]

        finally:
            # Restore
            if orig_doc.exists():
                orig_doc.unlink()
            backup_doc.rename(orig_doc)
