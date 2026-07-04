"""Milestone 3 verifier for the viewport snapshot engine.

Each test runs the agent's /app/viewport.py as a black box and compares its
snapshot records against an independent reference (reference.py, mounted only at
verify time and never present in the agent image) that selects candidates and
sorts them a second way. Inputs pin the cases that decide correctness: reading
order broken by string id on ties, the role-only and onclick candidates, an
offscreen candidate that must be dropped, and label whitespace collapse with
truncation.
Run alone with: pytest tests/test_m3.py
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
    """Assert the engine's snapshot records equal the independent reference."""
    got = run_engine({"milestone": 3, "cases": cases})
    want = ref.canonical({"answers": [ref.run_milestone_3(c) for c in cases]})
    assert got == want, f"[{label}] mismatch\n  expected: {want[:600]}\n  got:      {got[:600]}"


class TestMilestone3:
    """Milestone 3: ordered interactive snapshot records."""

    def test_program_file_exists(self):
        """The agent must create the program at /app/viewport.py."""
        assert os.path.exists(ENGINE), f"{ENGINE} does not exist"

    def test_record_shape(self):
        """Records carry the fixed fields, indices count contiguously from zero,
        and labels never exceed fifty characters."""
        ans = json.loads(run_engine({"milestone": 3, "cases": ref.m3_designed()}))["answers"]
        for obj in ans:
            recs = obj["records"]
            assert [r["index"] for r in recs] == list(range(len(recs)))
            for r in recs:
                assert set(r) == {"index", "id", "tag", "role", "rect", "label"}
                assert isinstance(r["rect"], list) and len(r["rect"]) == 4
                assert len(r["label"]) <= 50

    def test_reading_order_and_membership(self):
        """Ties in reading order break by string id, the role-only candidate is
        kept while a plain node is dropped, and an offscreen candidate is absent."""
        cases = ref.m3_designed()
        order = json.loads(run_engine({"milestone": 3, "cases": [cases[0]]}))["answers"][0]
        assert [r["id"] for r in order["records"]] == ["e10", "e2", "e1"]
        gone = json.loads(run_engine({"milestone": 3, "cases": [cases[2]]}))["answers"][0]
        assert [r["id"] for r in gone["records"]] == ["seen"]

    def test_designed_cases(self):
        """Designed trees pin the id tie-break, the candidate rule, the dropped
        offscreen element, and label collapse and truncation."""
        for i, sc in enumerate(ref.m3_designed()):
            check([sc], f"designed[{i}]")

    def test_random_cases(self):
        """Randomized deep trees catch a wrong sort key, a wrong candidate set, or
        inclusion of an offscreen element."""
        for seed in range(12):
            rng = ref._rng(3000 + seed)
            check([ref.rand_case(rng) for _ in range(6)], f"random[{seed}]")
