"""Milestone 6 — hexadecimal ports, IPv6 peers, and deleted path suffixes."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

APP = Path("/app")
OUTPUT = APP / "output" / "policy_audit.json"
INDEX = APP / "output" / "trace_index.json"
JAR = APP / "build/libs/trace-audit-cli.jar"
RELAY_LANE = APP / "docs" / "q3_bundles" / "relay_lane.md"


@pytest.fixture(scope="module", autouse=True)
def regenerate_policy_audit() -> None:
    OUTPUT.unlink(missing_ok=True)
    subprocess.run(["bash", "/app/scripts/build_all.sh"], check=True)
    subprocess.run(["bash", "/app/scripts/milestone_probes.sh", "audit"], check=True)


def _load() -> dict:
    assert OUTPUT.is_file(), "policy_audit.json missing; run milestone_probes.sh audit"
    return json.loads(OUTPUT.read_text())


class TestMilestone6:
    def test_jar_exists(self) -> None:
        """Gradle build must produce the trace audit CLI jar."""
        assert JAR.is_file(), "JAR not built; run build_all.sh first"

    def test_jar_audit_produces_output_directly(self) -> None:
        """The audit CLI jar must emit policy audit JSON without probe-script shortcuts."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as audit_handle:
            audit_path = Path(audit_handle.name)
        try:
            subprocess.run(["java", "-jar", str(JAR), "index", str(INDEX)], check=True)
            result = subprocess.run(
                ["java", "-jar", str(JAR), "audit", str(INDEX), str(audit_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr
            data = json.loads(audit_path.read_text())
            assert "198.51.100.42:443" in data["socket_rows"]
            assert "[2001:db8::5]:443" in data["socket_rows"]
        finally:
            audit_path.unlink(missing_ok=True)

    def test_hex_port_peer(self) -> None:
        """Hexadecimal htons ports decode to decimal host:port peers."""
        data = _load()
        assert "198.51.100.42:443" in data["socket_rows"]

    def test_ipv6_peer_bracket_format(self) -> None:
        """Non-loopback IPv6 peers emit bracketed host:port labels."""
        data = _load()
        assert "[2001:db8::5]:443" in data["socket_rows"]

    def test_ipv6_loopback_excluded(self) -> None:
        """IPv6 loopback health checks stay out of socket_rows."""
        data = _load()
        assert not any("::1" in row for row in data["socket_rows"])
        egress = {
            v["detail"]
            for v in data["violations"]
            if v["kind"] == "network_egress"
        }
        assert not any("::1" in detail for detail in egress)

    def test_deleted_suffix_stripped(self) -> None:
        """Lsof (deleted) suffixes strip before in-run path comparison."""
        data = _load()
        details = {
            v["detail"]
            for v in data["violations"]
            if v["kind"] == "write_outside_run_dir"
        }
        assert "/var/lib/diffusion-runs/current/relay.log" not in details
        assert not any(detail.endswith("(deleted)") for detail in details)

    def test_out_of_run_deleted_path_still_flagged(self) -> None:
        """Stripping (deleted) must still flag paths outside run_dir."""
        original = RELAY_LANE.read_text()
        injection = (
            "88150 python  10w  REG  253,0  0  "
            "/etc/diffusion/stale/relay.bin (deleted)\n"
        )
        patched = original.replace("```lsof\n", f"```lsof\n{injection}", 1)
        RELAY_LANE.write_text(patched)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as audit_handle:
            audit_path = Path(audit_handle.name)
        try:
            subprocess.run(["bash", "/app/scripts/build_all.sh"], check=True)
            subprocess.run(["java", "-jar", str(JAR), "index", str(INDEX)], check=True)
            result = subprocess.run(
                ["java", "-jar", str(JAR), "audit", str(INDEX), str(audit_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr
            data = json.loads(audit_path.read_text())
            details = {
                v["detail"]
                for v in data["violations"]
                if v["kind"] == "write_outside_run_dir"
            }
            assert "/etc/diffusion/stale/relay.bin" in details
            assert not any(detail.endswith("(deleted)") for detail in details)
        finally:
            audit_path.unlink(missing_ok=True)
            RELAY_LANE.write_text(original)
            subprocess.run(["bash", "/app/scripts/build_all.sh"], check=True)
            subprocess.run(["bash", "/app/scripts/milestone_probes.sh", "audit"], check=True)

    def test_reversed_ipv4_field_order(self) -> None:
        """sin_port before sin_addr still reconstructs host:port peers."""
        original = RELAY_LANE.read_text()
        injection = (
            "88150 connect(10, {sa_family=AF_INET, sin_port=htons(8080), "
            'sin_addr=inet_addr("203.0.113.5")}, 16) = 0\n'
        )
        patched = original.replace("```strace\n", f"```strace\n{injection}", 1)
        RELAY_LANE.write_text(patched)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as audit_handle:
            audit_path = Path(audit_handle.name)
        try:
            subprocess.run(["bash", "/app/scripts/build_all.sh"], check=True)
            subprocess.run(["java", "-jar", str(JAR), "index", str(INDEX)], check=True)
            result = subprocess.run(
                ["java", "-jar", str(JAR), "audit", str(INDEX), str(audit_path)],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, result.stderr
            data = json.loads(audit_path.read_text())
            assert "203.0.113.5:8080" in data["socket_rows"]
        finally:
            audit_path.unlink(missing_ok=True)
            RELAY_LANE.write_text(original)
            subprocess.run(["bash", "/app/scripts/build_all.sh"], check=True)
            subprocess.run(["bash", "/app/scripts/milestone_probes.sh", "audit"], check=True)

    def test_relay_lane_network_egress(self) -> None:
        """Relay-lane strace contributes remote egress findings."""
        data = _load()
        relay = [
            v
            for v in data["violations"]
            if v["kind"] == "network_egress" and v["source"] == "relay_lane.md"
        ]
        assert len(relay) >= 1
        assert any(v["detail"] == "198.51.100.42:443" for v in relay)
