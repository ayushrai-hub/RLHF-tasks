"""Milestone 2 — reconstruct strace peers and paths."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

OUTPUT = Path("/app/output/policy_audit.json")
JAR = Path("/app/build/libs/trace-audit-cli.jar")
RUN_DIR = "/var/lib/diffusion-runs/current"


@pytest.fixture(scope="module", autouse=True)
def regenerate_policy_audit() -> None:
    OUTPUT.unlink(missing_ok=True)
    subprocess.run(["bash", "/app/scripts/build_all.sh"], check=True)
    subprocess.run(["bash", "/app/scripts/milestone_probes.sh", "audit"], check=True)


def _load() -> dict:
    assert OUTPUT.is_file(), "policy_audit.json missing; run milestone_probes.sh audit"
    return json.loads(OUTPUT.read_text())


class TestMilestone2:
    def test_jar_exists(self) -> None:
        """Gradle build must produce the trace audit CLI jar."""
        assert JAR.is_file(), "JAR not built; run build_all.sh first"

    def test_audit_probe_regenerates_output(self) -> None:
        """Audit probe must regenerate policy_audit.json from the jar."""
        assert OUTPUT.is_file()

    def test_audit_schema(self) -> None:
        """Audit JSON carries the milestone schema tag."""
        data = _load()
        assert data["schema_tag"] == "tb3-kdiff-trace-02"

    def test_run_dir(self) -> None:
        """Audit output echoes the configured run directory."""
        data = _load()
        assert data["run_dir"] == RUN_DIR

    def test_socket_rows(self) -> None:
        """Remote peers are reconstructed from strace connect lines."""
        data = _load()
        assert "93.184.216.34:443" in data["socket_rows"]
        assert len(data["socket_rows"]) == 1

    def test_loopback_excluded_from_socket_rows(self) -> None:
        """Loopback health-check connects stay out of socket_rows."""
        data = _load()
        peers = {row.split(":")[0] for row in data["socket_rows"]}
        assert "127.0.0.1" not in peers
        assert not any(peer.startswith("127.") for peer in peers)
        egress_details = {
            v["detail"]
            for v in data["violations"]
            if v["kind"] == "network_egress"
        }
        assert not any("127." in detail for detail in egress_details)

    def test_openat_outside_run_dir(self) -> None:
        """Out-of-run openat paths are parsed and surfaced as violations."""
        data = _load()
        outside_paths = [
            v
            for v in data["violations"]
            if v["kind"] == "write_outside_run_dir"
        ]
        details = {v["detail"] for v in outside_paths}
        assert "/etc/diffusion/cache/state.bin" in details
        assert "/tmp/diffusion-run/scratch.dat" in details
        assert "/var/tmp/diffusion/spill.bin" in details

    def test_strace_paths_from_multiple_runbooks(self) -> None:
        """Openat parsing covers strace excerpts beyond mirror_lane."""
        data = _load()
        sources = {
            v["source"]
            for v in data["violations"]
            if v["kind"] == "write_outside_run_dir"
        }
        assert "burst_lane.md" in sources
        assert "cache_spill.md" in sources
