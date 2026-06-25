"""Milestone 1 — index trace documentation bundles."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

import pytest

APP = Path("/app")
OUTPUT = APP / "output" / "trace_index.json"
JAR = APP / "build" / "libs" / "trace-audit-cli.jar"
BUNDLES = APP / "docs" / "q3_bundles"
RUNBOOK_FILES = {path.name for path in BUNDLES.glob("*.md")}


@pytest.fixture(scope="module", autouse=True)
def regenerate_trace_index() -> None:
    OUTPUT.unlink(missing_ok=True)
    subprocess.run(["bash", "/app/scripts/build_all.sh"], check=True)
    subprocess.run(["bash", "/app/scripts/milestone_probes.sh", "index"], check=True)


def _load() -> dict:
    assert OUTPUT.is_file(), "trace_index.json missing; run milestone_probes.sh index"
    return json.loads(OUTPUT.read_text())


def _fence_count(kind: str) -> int:
    total = 0
    for path in sorted(BUNDLES.glob("*.md")):
        text = path.read_text()
        marker = f"```{kind}"
        start = 0
        while True:
            idx = text.find(marker, start)
            if idx < 0:
                break
            total += 1
            start = idx + len(marker)
    return total


def _expected_harvested_blocks() -> list[dict[str, object]]:
    fence_pattern = re.compile(r"```(strace|lsof)\n(.*?)```", re.DOTALL)
    blocks: list[dict[str, object]] = []
    for path in sorted(BUNDLES.glob("*.md")):
        text = path.read_text()
        for match in fence_pattern.finditer(text):
            body = "\n".join(line.rstrip() for line in match.group(2).strip().splitlines())
            if not body:
                continue
            blocks.append(
                {
                    "source_path": path.name,
                    "fence_kind": match.group(1),
                    "line_count": len(body.splitlines()),
                }
            )
    return sorted(blocks, key=lambda block: (block["source_path"], block["fence_kind"]))


class TestMilestone1:
    def test_jar_exists(self) -> None:
        """Gradle build must produce the trace audit CLI jar."""
        assert JAR.is_file(), "JAR not built; run build_all.sh first"

    def test_jar_produces_output_directly(self) -> None:
        """The harvest CLI jar must emit a valid index without probe-script shortcuts."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
            out_path = Path(handle.name)
        try:
            result = subprocess.run(
                ["java", "-jar", str(JAR), "index", str(out_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr
            data = json.loads(out_path.read_text())
            assert data["trace_blocks"] == 15
        finally:
            out_path.unlink(missing_ok=True)

    def test_index_probe_regenerates_output(self) -> None:
        """Index probe must regenerate trace_index.json from the jar."""
        assert OUTPUT.is_file()

    def test_index_schema(self) -> None:
        """Index JSON carries the milestone schema tag."""
        data = _load()
        assert data["schema_tag"] == "tb3-kdiff-trace-01"

    def test_sources_scanned(self) -> None:
        """All seven runbooks are indexed."""
        data = _load()
        assert data["sources_scanned"] == 7

    def test_harvest_block_count(self) -> None:
        """Every fenced trace excerpt is harvested."""
        data = _load()
        expected = _fence_count("strace") + _fence_count("lsof")
        assert expected == 15
        assert data["trace_blocks"] == expected

    def test_lsof_blocks_present(self) -> None:
        """Both strace and lsof fence kinds appear."""
        data = _load()
        kinds = set(data["fence_kinds"])
        assert kinds == {"strace", "lsof"}

    def test_per_block_fence_kind(self) -> None:
        """Each harvested block records the correct fence kind."""
        data = _load()
        strace_count = sum(1 for block in data["blocks"] if block["fence_kind"] == "strace")
        lsof_count = sum(1 for block in data["blocks"] if block["fence_kind"] == "lsof")
        assert strace_count == _fence_count("strace")
        assert lsof_count == _fence_count("lsof")

    def test_block_line_counts(self) -> None:
        """Each harvested block reports a positive line_count matching the fence body."""
        data = _load()
        expected = _expected_harvested_blocks()
        actual = sorted(
            data["blocks"],
            key=lambda block: (block["source_path"], block["fence_kind"]),
        )
        assert len(actual) == len(expected)
        for block, spec in zip(actual, expected, strict=True):
            assert block["line_count"] == spec["line_count"]
            assert block["line_count"] > 0

    def test_source_paths_populated(self) -> None:
        """Each harvested block records its runbook path."""
        data = _load()
        paths = {block["source_path"] for block in data["blocks"]}
        for block in data["blocks"]:
            assert block["source_path"] in RUNBOOK_FILES, (
                f"source_path '{block['source_path']}' not a real runbook"
            )
        assert len(paths) == 7, "All seven runbooks should appear in harvested blocks"
