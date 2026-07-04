"""Tests for video-segment-coassigner (TypeScript optimization archetype)."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "/tests")

from model import evaluate as base_evaluate  # noqa: E402
from model_for_tests import strict_evaluate  # noqa: E402

INPUT = Path("/app/task_file/input_data")
OUTPUT = Path("/app/task_file/output_data")
SRCDIR = Path("/app/task_file/src")
SRC = SRCDIR / "Main.ts"
JS = SRCDIR / "Main.js"

INPUT_HASHES = {
    "segments.jsonl": "6fbc61274a163cec3e10ef656a241bc4fd58ce7a75bc0b8489040a4a11924782",
    "node_config.json": "6d20a9233139a05af9e1fbacbaafa02b476b6843f93bd76bb8065d42a34b8b8e",
}
SCORE_THRESHOLD = 0.925
STRICT_THRESHOLD = 0.925
PROBE_THRESHOLD = 0.60


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _compile_ts():
    return subprocess.run(
        ["npx", "tsc"],
        cwd=str(SRCDIR),
        env={**os.environ, "HOME": "/root"},
        capture_output=True, text=True, timeout=120,
    )


def _run_node(input_dir, output_dir):
    return subprocess.run(
        ["node", str(JS), str(input_dir), str(output_dir)],
        env={**os.environ, "HOME": "/root"},
        capture_output=True, text=True, timeout=120,
    )


def _load_assignment():
    rows = []
    with open(OUTPUT / "assignment.jsonl") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _segments():
    items = {}
    for line in (INPUT / "segments.jsonl").read_text().splitlines():
        if line.strip():
            s = json.loads(line)
            items[s["segment_id"]] = s
    return items


def _nodes():
    cfg = json.loads((INPUT / "node_config.json").read_text())
    return {b["node_id"]: b for b in cfg["nodes"]}


class TestInputIntegrity:
    def test_segments_hash(self):
        """Verify the segment list has not been modified."""
        assert _sha256(INPUT / "segments.jsonl") == INPUT_HASHES["segments.jsonl"], \
            "segments.jsonl has been modified"

    def test_node_config_hash(self):
        """Verify the node config has not been modified."""
        assert _sha256(INPUT / "node_config.json") == INPUT_HASHES["node_config.json"], \
            "node_config.json has been modified"



class TestOutputExists:
    def test_assignment_exists(self):
        """The optimizer must write assignment.jsonl into output_data/."""
        assert (OUTPUT / "assignment.jsonl").exists(), "assignment.jsonl not found in output_data/"


class TestOutputSchema:
    def test_every_segment_assigned_once(self):
        """Every segment must be assigned exactly once."""
        rows = _load_assignment()
        items = _segments()
        ids = [r["segment_id"] for r in rows]
        assert len(ids) == len(items), f"Expected {len(items)} assignments, got {len(ids)}"
        assert len(set(ids)) == len(items), "Duplicate segment_ids found"

    def test_all_node_ids_valid(self):
        """Every node_id referenced must exist in the node config."""
        rows = _load_assignment()
        valid = set(_nodes())
        bad = [r["node_id"] for r in rows if r["node_id"] not in valid]
        assert not bad, f"Invalid node_ids: {bad[:5]}"

    def test_capacity_respected(self):
        """No node may exceed its CPU or bitrate capacity."""
        rows = _load_assignment()
        items, nodes = _segments(), _nodes()
        cpu = {nid: 0 for nid in nodes}
        bitrate = {nid: 0 for nid in nodes}
        for r in rows:
            cpu[r["node_id"]] += items[r["segment_id"]]["cpu"]
            bitrate[r["node_id"]] += items[r["segment_id"]]["bitrate"]
        for nid in nodes:
            assert cpu[nid] <= nodes[nid]["cpu_capacity"], f"{nid} cpu overflow"
            assert bitrate[nid] <= nodes[nid]["bitrate_capacity"], f"{nid} bitrate overflow"


class TestHardConstraints:
    def test_no_penalty(self):
        """No hard constraint may be violated."""
        result = base_evaluate(str(INPUT), str(OUTPUT))
        assert "penalty" not in result, \
            f"Hard constraint violated: {result.get('penalty')} — {result.get('detail', '')}"


class TestScoreThreshold:
    def test_base_score(self):
        """The base weighted score must reach the required threshold."""
        result = base_evaluate(str(INPUT), str(OUTPUT))
        score = result.get("total_score", 0.0)
        assert score >= SCORE_THRESHOLD, (
            f"Base score {score:.4f} < {SCORE_THRESHOLD}. "
            f"aff={result.get('affinity_score')}, cpu_bal={result.get('cpu_balance_score')}, "
            f"br_bal={result.get('bitrate_balance_score')}, "
            f"forbidden={result.get('forbidden_co_located')}"
        )


class TestStrictScore:
    def test_strict_score(self):
        """The strict score (after assignment-quality gates) must clear the bar."""
        result = strict_evaluate(str(INPUT), str(OUTPUT))
        strict = result.get("total_score_strict", 0.0)
        assert strict >= STRICT_THRESHOLD, (
            f"Strict score {strict:.4f} < {STRICT_THRESHOLD} (quality gates not met). "
            f"Full result: {result}"
        )


class TestTsImplementation:
    def test_ts_source_present(self):
        """The TypeScript source Main.ts must be present."""
        assert SRC.exists(), "Main.ts not found under src/"

    def test_source_is_not_a_shellout(self):
        """The solution source must be TypeScript, not a Python shell-out."""
        content = SRC.read_text(errors="ignore")
        assert "python" not in content.lower(), "Solution must not invoke Python"

    def test_typescript_compiles(self):
        """`npx tsc` must compile Main.ts to Main.js with no errors."""
        if JS.exists():
            JS.unlink()
        comp = _compile_ts()
        assert comp.returncode == 0, f"tsc failed: {comp.stdout[:400]} {comp.stderr[:400]}"
        assert JS.exists(), "tsc did not emit Main.js"

    def test_compiled_program_produces_output(self):
        """Recompiling and running with node must regenerate a high-scoring assignment."""
        comp = _compile_ts()
        assert comp.returncode == 0, f"tsc failed: {comp.stdout[:400]} {comp.stderr[:400]}"
        fresh = OUTPUT / "assignment.jsonl"
        if fresh.exists():
            fresh.unlink()
        res = _run_node(INPUT, OUTPUT)
        assert res.returncode == 0, f"node exited {res.returncode}: {res.stderr[:300]}"
        assert fresh.exists(), "node did not write assignment.jsonl"
        base = base_evaluate(str(INPUT), str(OUTPUT))
        assert base.get("total_score", 0.0) >= SCORE_THRESHOLD, \
            f"Fresh output base score too low: {base.get('total_score')}"
        strict = strict_evaluate(str(INPUT), str(OUTPUT))
        assert strict.get("total_score_strict", 0.0) >= STRICT_THRESHOLD, \
            f"Fresh output strict score too low: {strict.get('total_score_strict')}"

    def test_program_reads_node_config(self):
        """Program must read node_config.json dynamically (anti-hardcoding probe)."""
        import shutil
        if not JS.exists():
            assert _compile_ts().returncode == 0, "tsc failed"
        original = INPUT / "node_config.json"
        backup = INPUT / "node_config.json.bak"
        config = json.loads(original.read_text())
        modified = {"nodes": []}
        for nd in config["nodes"]:
            d = dict(nd)
            if d["node_id"] == "NODE-0":
                d["cpu_capacity"] = 200
                d["bitrate_capacity"] = 200
            modified["nodes"].append(d)
        try:
            shutil.copy(str(original), str(backup))
            original.write_text(json.dumps(modified))
            fresh = OUTPUT / "assignment.jsonl"
            if fresh.exists():
                fresh.unlink()
            res = _run_node(INPUT, OUTPUT)
            assert res.returncode == 0, f"node exited {res.returncode} with modified config: {res.stderr[:300]}"
            probe = base_evaluate(str(INPUT), str(OUTPUT))
            assert "penalty" not in probe, \
                f"Program violated constraints under modified config: {probe.get('penalty')}"
            assert probe.get("total_score", 0.0) >= PROBE_THRESHOLD, \
                f"Program score too low under modified config: {probe.get('total_score')}"
        finally:
            if backup.exists():
                shutil.copy(str(backup), str(original))
                backup.unlink()
