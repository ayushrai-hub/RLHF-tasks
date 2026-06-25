"""Milestone 7 — relay runbook cleanup and manifest verification."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

OUTPUT = Path("/app/output/verification_report.json")
BUNDLES = Path("/app/docs/q3_bundles")
RELAY = BUNDLES / "relay_lane.md"


@pytest.fixture(scope="module", autouse=True)
def regenerate_verification_report() -> None:
    OUTPUT.unlink(missing_ok=True)
    subprocess.run(["bash", "/app/scripts/build_all.sh"], check=True)
    subprocess.run(["bash", "/app/scripts/milestone_probes.sh", "verify"], check=True)


def _load() -> dict:
    assert OUTPUT.is_file(), "verification_report.json missing; run milestone_probes.sh verify"
    return json.loads(OUTPUT.read_text())


def _fence_body(text: str, label: str) -> str:
    marker = f"```{label}"
    start = text.index(marker)
    body_start = text.index("\n", start) + 1
    end = text.index("```", body_start)
    return text[body_start:end]


class TestMilestone7:
    def test_verification_schema(self) -> None:
        """Verify JSON carries the milestone schema tag."""
        data = _load()
        assert data["schema_tag"] == "tb3-kdiff-trace-04"

    def test_manifest_version(self) -> None:
        """Verify pass echoes the scenario manifest version."""
        data = _load()
        assert data["manifest_version"] == "2024.06"

    def test_bundle_and_block_counts(self) -> None:
        """Harvest totals match the scenario manifest."""
        data = _load()
        assert data["bundles_scanned"] == 7
        assert data["trace_blocks_harvested"] == 15
        assert data["manifest_sources_match"] is True
        assert data["manifest_blocks_match"] is True

    def test_audit_clean(self) -> None:
        """No policy violations remain after relay cleanup."""
        data = _load()
        assert data["audit_clean"] is True

    def test_relay_lane_offline_flag(self) -> None:
        """Verify pass reports relay lane as offline."""
        data = _load()
        assert data["relay_lane_offline"] is True

    def test_relay_strace_no_connect(self) -> None:
        """Relay strace excerpt no longer documents remote connects."""
        text = RELAY.read_text()
        assert "connect(" not in _fence_body(text, "strace")

    def test_relay_no_etc_paths(self) -> None:
        """Relay fenced excerpts keep state under the run directory."""
        text = RELAY.read_text()
        strace = _fence_body(text, "strace")
        lsof = _fence_body(text, "lsof")
        assert "/etc/diffusion" not in strace
        assert "/etc/diffusion" not in lsof
        assert "/var/lib/diffusion-runs/current" in strace

    def test_relay_lsof_no_remote_tcp(self) -> None:
        """Relay lsof excerpt no longer lists remote TCP rows."""
        text = RELAY.read_text()
        lsof = _fence_body(text, "lsof")
        assert "->" not in lsof
        assert "ESTABLISHED" not in lsof
