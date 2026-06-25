"""Milestone 4 — shell snippets and deduplicated policy audit."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

OUTPUT = Path("/app/output/policy_audit.json")
JAR = Path("/app/build/libs/trace-audit-cli.jar")
RUN_DIR = "/var/lib/diffusion-runs/current"
BURST_LANE = Path("/app/docs/q3_bundles/burst_lane.md")


@pytest.fixture(scope="module", autouse=True)
def regenerate_policy_audit() -> None:
    OUTPUT.unlink(missing_ok=True)
    subprocess.run(["bash", "/app/scripts/build_all.sh"], check=True)
    subprocess.run(["bash", "/app/scripts/milestone_probes.sh", "audit"], check=True)


def _load() -> dict:
    assert OUTPUT.is_file(), "policy_audit.json missing; run milestone_probes.sh audit"
    return json.loads(OUTPUT.read_text())


def _fd_delta(detail: str) -> int:
    if detail.startswith("fd_delta="):
        return int(detail.split("=", 1)[1])
    return int(detail)


class TestMilestone4:
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

    def test_violation_count(self) -> None:
        """Current runbooks surface nine deduplicated policy violations."""
        data = _load()
        assert data["violation_count"] == 9

    def test_violation_dedup(self) -> None:
        """Violation rows are deduplicated before counting."""
        data = _load()
        triples = {(v["kind"], v["source"], v["detail"]) for v in data["violations"]}
        assert len(triples) == len(data["violations"])

    def test_violation_kinds(self) -> None:
        """All four policy kinds are represented."""
        data = _load()
        kinds = set(data["violation_kinds"])
        assert kinds == {
            "rng_unseeded",
            "write_outside_run_dir",
            "descriptor_leak",
            "network_egress",
        }

    def test_socket_rows(self) -> None:
        """Remote peers are reconstructed from strace connect lines."""
        data = _load()
        assert "93.184.216.34:443" in data["socket_rows"]

    def test_network_egress_details(self) -> None:
        """network_egress violations record reconstructed peer details."""
        data = _load()
        egress = [v for v in data["violations"] if v["kind"] == "network_egress"]
        details = {v["detail"] for v in egress}
        assert "93.184.216.34:443" in details

    def test_out_of_run_writes(self) -> None:
        """Writes outside the run directory are reported."""
        data = _load()
        details = {v["detail"] for v in data["violations"] if v["kind"] == "write_outside_run_dir"}
        assert "/etc/diffusion/cache/state.bin" in details
        assert "/tmp/diffusion-run/scratch.dat" in details
        assert "/etc/diffusion/stale/relay.bin" in details

    def test_descriptor_leak_details(self) -> None:
        """descriptor_leak findings cite burst lane FD growth above threshold."""
        data = _load()
        leaks = [v for v in data["violations"] if v["kind"] == "descriptor_leak"]
        burst_leaks = [v for v in leaks if "burst_lane" in v["source"]]
        assert len(burst_leaks) >= 1
        assert any(_fd_delta(v["detail"]) > 4 for v in burst_leaks)
        warmup_leaks = [v for v in leaks if "warmup_lane" in v["source"]]
        assert not warmup_leaks, "equality at fd_leak_threshold must not fire descriptor_leak"

    def test_rng_unseeded_findings(self) -> None:
        """Documented sampler launches without --seed are flagged."""
        data = _load()
        rng = [v for v in data["violations"] if v["kind"] == "rng_unseeded"]
        assert len(rng) >= 2
        sources = {v["source"] for v in rng}
        assert "burst_lane.md" in sources
        assert "replay_lane.md" in sources
        assert all(v["detail"] for v in rng)

    def test_run_dir(self) -> None:
        """Audit output echoes the configured run directory."""
        data = _load()
        assert data["run_dir"] == RUN_DIR

    def test_audit_responds_to_input_change(self) -> None:
        """Injecting a new out-of-run openat path must surface an additional violation."""
        original = BURST_LANE.read_text()
        patched = original.replace(
            '66120 write(12, "tmp", 3) = 3',
            '66120 write(12, "tmp", 3) = 3\n'
            '66120 openat(AT_FDCWD, "/opt/rogue.dat", O_WRONLY) = 20',
        )
        BURST_LANE.write_text(patched)
        try:
            subprocess.run(["bash", "/app/scripts/build_all.sh"], check=True)
            subprocess.run(["bash", "/app/scripts/milestone_probes.sh", "audit"], check=True)
            data = json.loads(OUTPUT.read_text())
            assert data["violation_count"] > 9
            details = {
                v["detail"]
                for v in data["violations"]
                if v["kind"] == "write_outside_run_dir"
            }
            assert "/opt/rogue.dat" in details
        finally:
            BURST_LANE.write_text(original)
            subprocess.run(["bash", "/app/scripts/build_all.sh"], check=True)
            subprocess.run(["bash", "/app/scripts/milestone_probes.sh", "audit"], check=True)
