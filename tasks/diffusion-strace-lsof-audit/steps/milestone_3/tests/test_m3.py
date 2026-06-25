"""Milestone 3 — lsof continuation rows and descriptor leak thresholds."""

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


def _fd_delta(detail: str) -> int:
    if detail.startswith("fd_delta="):
        return int(detail.split("=", 1)[1])
    return int(detail)


class TestMilestone3:
    def test_jar_exists(self) -> None:
        """Gradle build must produce the trace audit CLI jar."""
        assert JAR.is_file(), "JAR not built; run build_all.sh first"

    def test_audit_schema_fields(self) -> None:
        """Audit JSON carries the contract schema fields and consistent counts."""
        data = _load()
        assert data["schema_tag"] == "tb3-kdiff-trace-02"
        assert data["violation_count"] == len(data["violations"])
        assert "descriptor_leak" in data["violation_kinds"]
        assert "write_outside_run_dir" in data["violation_kinds"]
        assert data["run_dir"] == RUN_DIR

    def test_descriptor_leak_details(self) -> None:
        """descriptor_leak findings cite burst lane FD growth above threshold."""
        data = _load()
        leaks = [v for v in data["violations"] if v["kind"] == "descriptor_leak"]
        burst_leaks = [v for v in leaks if "burst_lane" in v["source"]]
        assert len(burst_leaks) >= 1
        assert any(_fd_delta(v["detail"]) == 5 for v in burst_leaks)
        assert any(_fd_delta(v["detail"]) > 4 for v in burst_leaks)

    def test_warmup_near_threshold_no_leak(self) -> None:
        """Paired warmup snapshots at the threshold do not emit descriptor_leak."""
        data = _load()
        warmup_leaks = [
            v
            for v in data["violations"]
            if v["kind"] == "descriptor_leak" and "warmup_lane" in v["source"]
        ]
        assert not warmup_leaks

    def test_lsof_write_outside_cache(self) -> None:
        """Cache spill state path outside run_dir is reported."""
        data = _load()
        details = {v["detail"] for v in data["violations"] if v["kind"] == "write_outside_run_dir"}
        assert "/etc/diffusion/cache/state.bin" in details

    def test_lsof_write_outside_burst_scratch(self) -> None:
        """Burst scratch path outside run_dir is reported."""
        data = _load()
        details = {v["detail"] for v in data["violations"] if v["kind"] == "write_outside_run_dir"}
        assert "/tmp/diffusion-run/scratch.dat" in details

    def test_spill_bin_outside_run_dir(self) -> None:
        """Cache spill strace path outside run_dir is reported."""
        data = _load()
        details = {v["detail"] for v in data["violations"] if v["kind"] == "write_outside_run_dir"}
        assert "/var/tmp/diffusion/spill.bin" in details
