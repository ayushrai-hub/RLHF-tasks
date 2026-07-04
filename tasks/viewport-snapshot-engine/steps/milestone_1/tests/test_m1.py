"""Milestone 1 verifier for the viewport snapshot engine.

Each test runs the agent's /app/viewport.py as a black box on a JSON scenario and
compares its absolute layout against an independent reference (reference.py,
mounted only at verify time and never present in the agent image) that threads the
content origin through the box model a second way. Inputs concentrate on the cases
that decide correctness: a deep chain where border, padding and scroll accumulate
at every level, scroll that pushes children to negative coordinates, and a content
origin set by border and padding insets.
Run alone with: pytest tests/test_m1.py
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
    """Assert the engine's absolute layout equals the independent reference."""
    got = run_engine({"milestone": 1, "cases": cases})
    want = ref.canonical({"answers": [ref.run_milestone_1(c) for c in cases]})
    assert got == want, f"[{label}] mismatch\n  expected: {want[:500]}\n  got:      {got[:500]}"


class TestMilestone1:
    """Milestone 1: absolute border boxes through the nested box model."""

    def test_program_file_exists(self):
        """The agent must create the program at /app/viewport.py."""
        assert os.path.exists(ENGINE), f"{ENGINE} does not exist"

    def test_output_is_canonical_json(self):
        """Output must be canonical {"answers": [...]} JSON, one map per case."""
        cases = ref.m1_designed()
        raw = run_engine({"milestone": 1, "cases": cases})
        obj = json.loads(raw)
        assert set(obj) == {"answers"}, "top-level object must hold exactly 'answers'"
        assert len(obj["answers"]) == len(cases), "one result per case, in order"
        assert raw == json.dumps(obj, sort_keys=True, separators=(",", ":")), (
            "output is not canonically serialized")

    def test_every_node_has_integer_box(self):
        """Every node id in the tree maps to a four-integer border box, including
        the deepest node of the accumulation chain."""
        ans = json.loads(run_engine({"milestone": 1, "cases": ref.m1_designed()}))["answers"]
        assert "L5" in ans[0], "deep chain must report every nested node"
        for amap in ans:
            for box in amap.values():
                assert isinstance(box, list) and len(box) == 4
                assert all(isinstance(v, int) for v in box)

    def test_designed_cases(self):
        """Designed trees pin the accumulation traps: borders, padding and scroll
        compounding down a deep chain, and the negated-scroll shift of children."""
        for i, sc in enumerate(ref.m1_designed()):
            check([sc], f"designed[{i}]")

    def test_random_cases(self):
        """Randomized deep trees catch absolute-coordinate or wrong-scroll-sign
        layout and a content origin missing the border or padding inset."""
        for seed in range(12):
            rng = ref._rng(1000 + seed)
            check([ref.rand_case(rng) for _ in range(6)], f"random[{seed}]")
