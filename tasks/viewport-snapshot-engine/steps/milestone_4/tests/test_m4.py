"""Milestone 4 verifier for the viewport snapshot engine.

Each test runs the agent's /app/viewport.py as a black box and compares its
binary snapshot frame against an independent reference (reference.py, mounted only
at verify time and never present in the agent image) that rebuilds the frame with
table-driven CRC and a separately written varint coder. Beyond comparing the
reported sha256, crc and length, the suite reconstructs the expected frame bytes
and hashes them here, so a single wrong byte anywhere in the header, the
length-prefixed strings, the signed delta varints, or the custom CRC fails.
Inputs pin the empty frame, a single record, negative deltas, the odd-count and
role and label flag bits, and signed two's-complement deltas.
Run alone with: pytest tests/test_m4.py
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reference as ref  # noqa: E402

ENGINE = "/app/viewport.py"


def run_engine(scenario, timeout=120):
    """Invoke /app/viewport.py on a scenario and return its raw output string."""
    with tempfile.TemporaryDirectory() as d:
        ip = os.path.join(d, "scenario.json")
        op = os.path.join(d, "out.json")
        with open(ip, "w") as f:
            json.dump(scenario, f)
        proc = subprocess.run([sys.executable, ENGINE, ip, op],
                              capture_output=True, text=True, timeout=timeout)
        assert proc.returncode == 0, (
            f"engine exited {proc.returncode}; stderr:\n{proc.stderr[:2000]}")
        assert os.path.exists(op), "engine did not write the output file"
        raw = open(op).read()
    json.loads(raw)
    return raw


def check(cases, label):
    """Assert the engine's frame summary equals the independent reference."""
    got = run_engine({"milestone": 4, "cases": cases})
    want = ref.canonical({"answers": [ref.run_milestone_4(c) for c in cases]})
    assert got == want, f"[{label}] mismatch\n  expected: {want[:600]}\n  got:      {got[:600]}"


class TestMilestone4:
    """Milestone 4: checksummed binary snapshot frame."""

    def test_program_file_exists(self):
        """The agent must create the program at /app/viewport.py."""
        assert os.path.exists(ENGINE), f"{ENGINE} does not exist"

    def test_summary_shape(self):
        """Each answer has a 64-char lowercase hex sha256, an integer crc within
        32 bits, an integer byte length, and an integer record count."""
        ans = json.loads(run_engine({"milestone": 4, "cases": ref.m4_designed()}))["answers"]
        hexchars = set("0123456789abcdef")
        for out in ans:
            assert set(out) == {"sha256", "crc", "length", "records"}
            assert len(out["sha256"]) == 64 and set(out["sha256"]) <= hexchars
            assert isinstance(out["crc"], int) and 0 <= out["crc"] <= 0xFFFFFFFF
            assert isinstance(out["length"], int) and isinstance(out["records"], int)

    def test_empty_frame(self):
        """A case with no candidates yields the empty frame DVS1, version, zero
        flags, a zero count, then the CRC, with a matching sha256 and length."""
        empty = {"viewport": [60, 60], "root": {"id": "root", "tag": "div",
                 "box": [0, 0, 60, 60], "children": [
                     {"id": "p", "tag": "div", "box": [0, 0, 10, 10], "text": "x"}]}}
        out = json.loads(run_engine({"milestone": 4, "cases": [empty]}))["answers"][0]
        frame, crc = ref.build_frame([])
        assert out["records"] == 0
        assert out["length"] == len(frame)
        assert out["crc"] == crc
        assert out["sha256"] == hashlib.sha256(frame).hexdigest()

    def test_frame_bytes_reconstruct(self):
        """Rebuild the expected frame bytes here and confirm the engine's reported
        sha256, crc and length match them on every designed case."""
        cases = ref.m4_designed()
        ans = json.loads(run_engine({"milestone": 4, "cases": cases}))["answers"]
        for case, out in zip(cases, ans):
            frame, crc = ref.build_frame(ref.run_milestone_3(case)["records"])
            assert out["sha256"] == hashlib.sha256(frame).hexdigest(), json.dumps(out)[:200]
            assert out["crc"] == crc and out["length"] == len(frame)

    def test_designed_cases(self):
        """Designed frames pin the empty frame, a single record, negative deltas,
        and the odd-count, role and label flag bits."""
        for i, sc in enumerate(ref.m4_designed()):
            check([sc], f"designed[{i}]")

    def test_random_cases(self):
        """Randomized deep trees catch a wrong delta, missing two's-complement
        encoding, a wrong flags byte, or the standard reflected CRC."""
        for seed in range(12):
            rng = ref._rng(4000 + seed)
            check([ref.rand_case(rng) for _ in range(6)], f"random[{seed}]")
