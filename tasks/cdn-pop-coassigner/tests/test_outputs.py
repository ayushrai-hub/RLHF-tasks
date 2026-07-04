"""Tests for cdn-pop-coassigner (Go FNV-cliff coassigner)."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/tests")

from model import evaluate as base_evaluate  # noqa: E402

INPUT = Path("/app/task_file/input_data")
OUTPUT = Path("/app/task_file/output_data")
SRCDIR = Path("/app/task_file/src")
SRC = SRCDIR / "main.go"

INPUT_HASHES = {
    "assets.jsonl": "3438eb3e4a9f717a9868cd6479ec8e09907a81300b764eadaca63aa0e701764f",
    "pops_config.json": "475fa043d4c74e574adecc78b06a3306dc2e509487be8a1a11f3a40267abec74",
}

SCORE_THRESHOLD = 0.67
STRICT_THRESHOLD = 0.67
PROBE_THRESHOLD = 0.57
AFF_GATE = 0.5
BAL_GATE = 0.93

_BUILT = {}


def strict_evaluate(input_dir, output_dir):
    base = base_evaluate(input_dir, output_dir)
    if "penalty" in base:
        return {**base, "total_score_strict": 0.0}
    score = base["total_score"]
    if base.get("affinity_score", 0.0) < AFF_GATE:
        score *= 0.55
    if base.get("balance_score", 0.0) < BAL_GATE:
        score *= 0.65
    return {**base, "total_score_strict": round(max(0.0, min(1.0, score)), 4)}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _build():
    """Recompile the agent's main.go ourselves (anti-cheat: not any prebuilt binary)."""
    if _BUILT.get("path") and Path(_BUILT["path"]).exists():
        return _BUILT["path"]
    if not (SRCDIR / "main.go").exists():
        return None
    outdir = tempfile.mkdtemp(prefix="verify_")
    binp = os.path.join(outdir, "optimizer")
    proc = subprocess.run(
        ["go", "build", "-o", binp, "."], cwd=str(SRCDIR),
        env={**os.environ, "HOME": "/root", "GOCACHE": "/tmp/gocache", "GOFLAGS": "-mod=mod"},
        capture_output=True, text=True, timeout=240,
    )
    if proc.returncode != 0 or not os.path.exists(binp):
        return None
    _BUILT["path"] = binp
    return binp


def _run(binp, input_dir, output_dir):
    return subprocess.run([str(binp), str(input_dir), str(output_dir)],
                          env={**os.environ, "HOME": "/root"}, capture_output=True, text=True, timeout=180)


def _load_assignment():
    rows = []
    with open(OUTPUT / "assignment.jsonl") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _items():
    items = {}
    for line in (INPUT / "assets.jsonl").read_text().splitlines():
        if line.strip():
            s = json.loads(line)
            items[s["asset_id"]] = s
    return items


def _buckets():
    cfg = json.loads((INPUT / "pops_config.json").read_text())
    return {b["pop_id"]: b for b in cfg["pops"]}


class TestInputIntegrity:
    def test_inputs_unmodified(self):
        """The bundled input files are read-only and must not be modified."""
        for name, want in INPUT_HASHES.items():
            assert _sha256(INPUT / name) == want, f"{name} has been modified - inputs are read-only"


class TestOutputExists:
    def test_assignment_exists(self):
        """The optimizer must write assignment.jsonl into output_data/."""
        assert (OUTPUT / "assignment.jsonl").exists(), "assignment.jsonl not found in output_data/"


class TestOutputSchema:
    def test_every_item_assigned_once(self):
        """Every asset must be assigned exactly once."""
        rows = _load_assignment()
        items = _items()
        ids = [r["asset_id"] for r in rows]
        assert len(ids) == len(items), f"Expected {len(items)} assignments, got {len(ids)}"
        assert len(set(ids)) == len(items), "Duplicate asset_id found"

    def test_all_bucket_ids_valid(self):
        """Every pop_id referenced must exist in the config."""
        rows = _load_assignment()
        valid = set(_buckets())
        bad = [r["pop_id"] for r in rows if r["pop_id"] not in valid]
        assert not bad, f"Invalid pop_id: {bad[:5]}"

    def test_capacity_respected(self):
        """No pop may exceed its bytes_capacity."""
        rows = _load_assignment()
        items, buckets = _items(), _buckets()
        load = {b: 0 for b in buckets}
        for r in rows:
            load[r["pop_id"]] += items[r["asset_id"]]["bytes"]
        for b in buckets:
            assert load[b] <= buckets[b]["bytes_capacity"], f"{b} bytes_capacity overflow"


class TestHardConstraints:
    def test_no_penalty(self):
        """No hard constraint may be violated."""
        result = base_evaluate(str(INPUT), str(OUTPUT))
        assert "penalty" not in result, \
            f"Hard constraint violated: {result.get('penalty')} - {result.get('detail', '')}"


class TestScoreThreshold:
    def test_base_score(self):
        """The base quality score must reach the required threshold."""
        result = base_evaluate(str(INPUT), str(OUTPUT))
        score = result.get("total_score", 0.0)
        assert score >= SCORE_THRESHOLD, (
            f"Base score {score:.4f} < {SCORE_THRESHOLD}. "
            f"aff={result.get('affinity_score')}, bal={result.get('balance_score')}, "
            f"forbidden={result.get('forbidden_co_located')}"
        )


class TestStrictScore:
    def test_strict_score(self):
        """The strict score (after quality gates) must clear the bar."""
        result = strict_evaluate(str(INPUT), str(OUTPUT))
        strict = result.get("total_score_strict", 0.0)
        assert strict >= STRICT_THRESHOLD, (
            f"Strict score {strict:.4f} < {STRICT_THRESHOLD} (quality gates not met). Full result: {result}"
        )


class TestGoImplementation:
    def test_go_source_present(self):
        """The Go source main.go must be present."""
        assert SRC.exists(), "main.go not found under src/"

    def test_recompiled_program_scores(self):
        """Recompiling and rerunning main.go must regenerate a high-scoring assignment."""
        binp = _build()
        assert binp is not None, "go build of src/main.go failed"
        td_out = tempfile.mkdtemp()
        res = _run(binp, INPUT, td_out)
        assert res.returncode == 0, f"go run failed: {res.stderr[:300]}"
        assert (Path(td_out) / "assignment.jsonl").exists(), "Go program did not write assignment.jsonl"
        base = base_evaluate(str(INPUT), td_out)
        assert base.get("total_score", 0.0) >= SCORE_THRESHOLD, \
            f"recompiled output base score too low: {base.get('total_score')}"
        strict = strict_evaluate(str(INPUT), td_out)
        assert strict.get("total_score_strict", 0.0) >= STRICT_THRESHOLD, \
            f"recompiled output strict score too low: {strict.get('total_score_strict')}"

    def test_program_reads_config_dynamically(self):
        """The program must read bytes_capacity fresh each run and stay feasible+scoring under modified configs."""
        binp = _build()
        assert binp is not None, "go build failed"
        cfg = json.loads((INPUT / "pops_config.json").read_text())
        buckets = cfg["pops"]
        total_demand = sum(it["bytes"] for it in _items().values())
        for shrink in ([0], [2, 4], [1, 3, 5]):
            td_in = tempfile.mkdtemp()
            td_out = tempfile.mkdtemp()
            mod = {"pops": []}
            for k, b in enumerate(buckets):
                bb = dict(b)
                if k in shrink:
                    bb["bytes_capacity"] = int(bb["bytes_capacity"] * 0.8)
                mod["pops"].append(bb)
            assert sum(b["bytes_capacity"] for b in mod["pops"]) > total_demand, "probe setup error: infeasible"
            (Path(td_in) / "assets.jsonl").write_text((INPUT / "assets.jsonl").read_text())
            (Path(td_in) / "pops_config.json").write_text(json.dumps(mod))
            res = _run(binp, td_in, td_out)
            assert res.returncode == 0, f"go failed on modified config: {res.stderr[:300]}"
            probe = base_evaluate(td_in, td_out)
            assert "penalty" not in probe, \
                f"constraint violated under modified config {shrink}: {probe.get('penalty')}"
            assert probe.get("total_score", 0.0) >= PROBE_THRESHOLD, \
                f"score too low under modified config {shrink}: {probe.get('total_score')}"
