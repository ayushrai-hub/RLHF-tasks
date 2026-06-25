"""Tests for milestone 3. Run alone with: pytest tests/test_m3.py"""

import json
import subprocess
from pathlib import Path


APP = Path("/app")
BIN = APP / "bin" / "gnvtlv"


def _build():
    BIN.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["go", "build", "-o", str(BIN), "./cmd/gnvtlv"],
        cwd=APP, capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"go build failed:\n{proc.stdout}\n{proc.stderr}"


def _audit(fixture: str, policy: str = "/app/configs/audit_policy.json") -> dict:
    _build()
    proc = subprocess.run(
        [str(BIN), "audit", "--in", str(APP / "testdata" / fixture), "--policy", policy],
        cwd=APP, capture_output=True, text=True,
    )
    assert proc.returncode == 0, f"audit {fixture} failed: {proc.stderr}"
    return json.loads(proc.stdout)


class TestMilestone3:
    """Tests for milestone 3: cascade-overrides-mute and per-class cap."""

    def test_milestone_1_artifact_persists(self) -> None:
        """Milestone 1 packages still pass (`go test ./internal/wire/... ./internal/decode/...`)."""
        proc = subprocess.run(
            ["go", "test", "./internal/wire/...", "./internal/decode/..."],
            cwd=APP, capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"M1 regressed:\n{proc.stdout}\n{proc.stderr}"

    def test_milestone_2_artifact_persists(self) -> None:
        """Milestone 2 package still passes (`go test ./internal/resolve/...`)."""
        proc = subprocess.run(
            ["go", "test", "./internal/resolve/..."],
            cwd=APP, capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"M2 regressed:\n{proc.stdout}\n{proc.stderr}"

    def test_audit_tests_pass(self) -> None:
        """`go test ./internal/audit/...` exits 0."""
        proc = subprocess.run(
            ["go", "test", "./internal/audit/..."],
            cwd=APP, capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"audit tests failed:\n{proc.stdout}\n{proc.stderr}"

    def test_full_suite_still_passes(self) -> None:
        """`go test ./...` exits 0 across the whole module."""
        proc = subprocess.run(
            ["go", "test", "./..."],
            cwd=APP, capture_output=True, text=True,
        )
        assert proc.returncode == 0, f"full suite failed:\n{proc.stdout}\n{proc.stderr}"

    def test_clean_packet_accepts(self) -> None:
        """A clean packet returns ACCEPT."""
        out = _audit("two_clean.bin")
        assert out["decision"] == "ACCEPT", out

    def test_critical_unknown_drops(self) -> None:
        """A critical+unknown option flips the decision to DROP."""
        out = _audit("unknown_crit.bin")
        assert out["decision"] == "DROP", out
        codes = [f["code"] for f in out["packet_findings"]]
        assert "UNKNOWN_CRITICAL" in codes, out

    def test_critical_unknown_drops_even_when_muted(self) -> None:
        """Muted UNKNOWN_CRITICAL still drops the packet (CASCADE_RULES §X.2.1)."""
        out = _audit("unknown_crit.bin", "/app/configs/audit_policy_muted.json")
        assert out["decision"] == "DROP", out
        assert out["override_applied"] is True, out
        # The packet-level finding records the override and is itself muted.
        unknowns = [f for f in out["packet_findings"] if f["code"] == "UNKNOWN_CRITICAL"]
        assert len(unknowns) == 1, out
        assert unknowns[0]["muted"] is True, unknowns[0]
        assert unknowns[0]["override_applied"] is True, unknowns[0]

    def test_non_critical_unknown_does_not_drop(self) -> None:
        """A non-critical unknown option does NOT flip the decision."""
        out = _audit("unknown_noncrit.bin")
        assert out["decision"] == "ACCEPT", out
        codes = [f["code"] for f in out["packet_findings"]]
        assert "UNKNOWN_CRITICAL" not in codes, out

    def test_max_per_class_drops_when_exceeded(self) -> None:
        """A packet exceeding the per-class cap drops (strict > boundary)."""
        out = _audit("three_class_0x0103.bin", "/app/configs/audit_policy_capped.json")
        assert out["decision"] == "DROP", out
        codes = [f["code"] for f in out["packet_findings"]]
        assert "MAX_PER_CLASS" in codes, out

    def test_max_per_class_exact_boundary_accepts(self) -> None:
        """A packet with exactly `cap` options per class still ACCEPTs."""
        # two_class_0x0103_boundary.bin has 2 options of class 0x0103; cap=2.
        out = _audit("two_class_0x0103_boundary.bin", "/app/configs/audit_policy_capped.json")
        assert out["decision"] == "ACCEPT", out
        codes = [f["code"] for f in out["packet_findings"]]
        assert "MAX_PER_CLASS" not in codes, out

    def test_unknown_critical_fires_once_per_packet(self) -> None:
        """Only one UNKNOWN_CRITICAL packet finding even if multiple options trigger it."""
        # Build a synthetic packet on the fly with two critical+unknown
        # options of different classes.
        import struct
        def opt(cls, t):
            return struct.pack(">HBB", cls, 0x80 | t, 0x00)
        pkt = struct.pack(">BBHBBBB", 0x02, 0x00, 0x6558, 0x01, 0x02, 0x03, 0x00) + opt(0xAAAA, 0x11) + opt(0xBBBB, 0x22)
        path = APP / "testdata" / "double_crit.bin"
        path.write_bytes(pkt)
        out = _audit("double_crit.bin")
        unknowns = [f for f in out["packet_findings"] if f["code"] == "UNKNOWN_CRITICAL"]
        assert len(unknowns) == 1, out

    def test_decision_is_exactly_accept_or_drop_string(self) -> None:
        """`decision` is `ACCEPT` or `DROP`, never anything else."""
        out = _audit("two_clean.bin")
        assert out["decision"] in {"ACCEPT", "DROP"}
        out = _audit("unknown_crit.bin")
        assert out["decision"] in {"ACCEPT", "DROP"}

    def test_options_total_and_recognized_counts(self) -> None:
        """`options_total` / `options_recognized` are JSON integers."""
        out = _audit("two_clean.bin")
        assert isinstance(out["options_total"], int) and not isinstance(out["options_total"], bool)
        assert isinstance(out["options_recognized"], int)
        assert out["options_total"] == 2
        assert out["options_recognized"] == 2

    def test_experimenter_nonempty_allowlist_denies_only_unlisted(self) -> None:
        """Non-empty allowlist permits listed vendors and denies the rest (CASCADE_RULES §X.4)."""
        out = _audit("two_experimenters.bin", "/app/configs/audit_policy.json")
        denied = [f for f in out["findings"] if f["code"] == "EXPERIMENTER_VENDOR_DENIED"]
        assert len(denied) == 1, denied
        assert denied[0]["opt_index"] == 1, denied

    def test_experimenter_empty_allowlist_denies_every_vendor(self) -> None:
        """An empty vendor_allowlist denies every experimenter-class option (CASCADE_RULES §X.4.1)."""
        out = _audit("two_experimenters.bin", "/app/configs/audit_policy_empty_vendor.json")
        denied = [f for f in out["findings"] if f["code"] == "EXPERIMENTER_VENDOR_DENIED"]
        assert len(denied) == 2, denied
        assert sorted(f["opt_index"] for f in denied) == [0, 1], denied

    def test_oam_packet_bypasses_unknown_critical_cascade(self) -> None:
        """OAM packets are exempt from §X.2 (CASCADE_RULES §X.5)."""
        out = _audit("oam_unknown_crit.bin")
        assert out["decision"] == "ACCEPT", out
        codes = [f["code"] for f in out["packet_findings"]]
        assert "UNKNOWN_CRITICAL" not in codes, out
        assert out["override_applied"] is False, out

    def test_oam_packet_exemption_applies_even_when_muted(self) -> None:
        """Per §X.5 the OAM exemption is independent of policy mute state."""
        out = _audit("oam_unknown_crit.bin", "/app/configs/audit_policy_muted.json")
        assert out["decision"] == "ACCEPT", out
        assert out["override_applied"] is False, out
        codes = [f["code"] for f in out["packet_findings"]]
        assert "UNKNOWN_CRITICAL" not in codes, out

    def test_oam_clean_packet_unchanged(self) -> None:
        """An OAM packet with no cascade trigger ACCEPTs the same as a non-OAM clean packet."""
        out = _audit("oam_clean.bin")
        assert out["decision"] == "ACCEPT", out

    def test_non_oam_critical_unknown_still_drops(self) -> None:
        """The §X.5 exemption applies ONLY to OAM packets (O=1); without OAM the cascade fires."""
        out = _audit("unknown_crit.bin")
        assert out["decision"] == "DROP", out
        codes = [f["code"] for f in out["packet_findings"]]
        assert "UNKNOWN_CRITICAL" in codes, out
