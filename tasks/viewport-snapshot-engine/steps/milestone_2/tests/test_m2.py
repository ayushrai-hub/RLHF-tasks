"""Milestone 2 verifier for the viewport snapshot engine.

Each test runs the agent's /app/viewport.py as a black box and compares its
clip-resolved visibility against an independent reference (reference.py, mounted
only at verify time and never present in the agent image) that collects the full
list of clipping ancestors and folds their padding boxes a second way. Inputs pin
the cases that decide correctness: clipping to the padding box rather than the
border or content box, nested clips, the half-open viewport edge, and the rule
that a clipping node never clips itself.
Run alone with: pytest tests/test_m2.py
"""
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
    """Assert the engine's clipped visibility equals the independent reference."""
    got = run_engine({"milestone": 2, "cases": cases})
    want = ref.canonical({"answers": [ref.run_milestone_2(c) for c in cases]})
    assert got == want, f"[{label}] mismatch\n  expected: {want[:600]}\n  got:      {got[:600]}"


class TestMilestone2:
    """Milestone 2: overflow and viewport clipping into visible rectangles."""

    def test_program_file_exists(self):
        """The agent must create the program at /app/viewport.py."""
        assert os.path.exists(ENGINE), f"{ENGINE} does not exist"

    def test_field_shape(self):
        """Every node maps to an onscreen boolean and a four-integer rect, with the
        rect zeroed when the node is offscreen."""
        ans = json.loads(run_engine({"milestone": 2, "cases": ref.m2_designed()}))["answers"]
        for amap in ans:
            for v in amap.values():
                assert set(v) == {"onscreen", "rect"}
                assert isinstance(v["onscreen"], bool)
                assert isinstance(v["rect"], list) and len(v["rect"]) == 4
                assert all(isinstance(c, int) for c in v["rect"])
                if not v["onscreen"]:
                    assert v["rect"] == [0, 0, 0, 0]

    def test_self_clip_and_padding_box(self):
        """A clipping node does not clip itself, and descendants clip to the
        padding box, so the border-inset edge child survives only where expected."""
        cases = ref.m2_designed()
        check([cases[0]], "padding-box-edge")
        check([cases[3]], "no-self-clip")

    def test_designed_cases(self):
        """Designed trees pin padding-box clipping, nested clips, the half-open
        viewport edge, and a clipping node that never clips itself."""
        for i, sc in enumerate(ref.m2_designed()):
            check([sc], f"designed[{i}]")

    def test_random_cases(self):
        """Randomized deep trees catch clipping to the wrong box, a dropped viewport
        clip, or an inclusive intersection at the edge."""
        for seed in range(12):
            rng = ref._rng(2000 + seed)
            check([ref.rand_case(rng) for _ in range(6)], f"random[{seed}]")
