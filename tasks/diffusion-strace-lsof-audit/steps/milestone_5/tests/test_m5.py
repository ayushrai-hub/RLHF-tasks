"""Milestone 5 — fix reproducibility violations in documented setup."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

APP = Path("/app")
OUTPUT = APP / "output" / "cleanup_report.json"
BUNDLES = APP / "docs" / "q3_bundles"


@pytest.fixture(scope="module", autouse=True)
def regenerate_cleanup_report() -> None:
    OUTPUT.unlink(missing_ok=True)
    subprocess.run(["bash", "/app/scripts/build_all.sh"], check=True)
    subprocess.run(["bash", "/app/scripts/milestone_probes.sh", "clean"], check=True)


def _runbook_digest() -> str:
    md = hashlib.sha256()
    for path in sorted(BUNDLES.glob("*.md")):
        md.update(path.read_bytes())
    return md.hexdigest()


def _load() -> dict:
    assert OUTPUT.is_file(), "cleanup_report.json missing; run milestone_probes.sh clean"
    return json.loads(OUTPUT.read_text())


class TestMilestone5:
    def test_cleanup_schema(self) -> None:
        """Cleanup JSON carries the milestone schema tag."""
        data = _load()
        assert data["schema_tag"] == "tb3-kdiff-trace-03"

    def test_open_violations(self) -> None:
        """No policy violations remain after runbook cleanup."""
        data = _load()
        assert data["open_violations"] == 0

    def test_policy_pass_count(self) -> None:
        """All four policy kinds pass."""
        data = _load()
        assert data["policy_pass_count"] == 4

    def test_runbook_sha256(self) -> None:
        """Runbook digest reflects repaired documentation."""
        data = _load()
        assert data["runbook_sha256"] == _runbook_digest()

    def test_seeded_replay_doc(self) -> None:
        """Replay runbook shell-invoke documents a seeded sampler launch."""
        replay = next(path for path in BUNDLES.glob("*.md") if "replay" in path.name)
        text = replay.read_text()
        marker = "<!-- shell-invoke -->"
        idx = text.index(marker)
        invoke_line = text[idx:].split("\n")[1]
        assert "--seed" in invoke_line

    def test_offline_mirror_doc(self) -> None:
        """Mirror runbook no longer documents remote pulls."""
        mirror = next(path for path in BUNDLES.glob("*.md") if "mirror" in path.name)
        text = mirror.read_text()
        assert "curl" not in text
        assert "connect(" not in text

    def test_run_dir_state_inside_workspace(self) -> None:
        """Cache runbook keeps state under the run directory."""
        cache = next(path for path in BUNDLES.glob("*.md") if "cache" in path.name)
        text = cache.read_text()
        assert "/etc/diffusion" not in text
        assert "/var/tmp/diffusion" not in text

    def test_burst_doc_flat_fd(self) -> None:
        """Burst runbook paired lsof snapshots stay flat."""
        burst = next(path for path in BUNDLES.glob("*.md") if "burst" in path.name)
        text = burst.read_text()
        assert "/tmp/diffusion-run" not in text
