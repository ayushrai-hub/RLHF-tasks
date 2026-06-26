import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

INPUT_DIR = Path("/app/task_file/input_data")
OUTPUT_DIR = Path("/app/task_file/output_data")
SCRIPTS_DIR = Path("/app/task_file/scripts")
BINARY = Path("/app/task_file/microgrid_restorer")

sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, "/tests")

from model import evaluate, microgrid_resonance_index  # noqa: E402
from model_for_tests import evaluate as strict_evaluate  # noqa: E402

MODEL_PY_SHA256 = "4fe527492f74a522af331466c31c2fc6e60f016361a4c735adbb974d6bd8d3ed"
FEEDERS_SHA256 = "ebf4ba279aaf20671d5bc0ff237523c34f801de98a8ffe84fb5cf48891fd730e"
CONFIG_SHA256 = "f0a6958644ed7dc5e2e9126fa1fcaf3120b55216160272080072949814cf2614"


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_plan():
    with open(OUTPUT_DIR / "restoration_plan.json", encoding="utf-8") as fh:
        return json.load(fh)


class TestMicrogridArtifactIntegrity:
    def test_visible_scorer_and_policy_inputs_are_unchanged(self):
        """The public scorer and calibrated microgrid inputs must match the shipped instance."""
        assert _sha256(SCRIPTS_DIR / "model.py") == MODEL_PY_SHA256
        assert _sha256(INPUT_DIR / "feeders.jsonl") == FEEDERS_SHA256
        assert _sha256(INPUT_DIR / "config.json") == CONFIG_SHA256


class TestRestorationPlanContract:
    def test_assignment_file_uses_the_required_shape(self):
        """The submitted plan is a JSON assignment list with one row per restored feeder."""
        plan_path = OUTPUT_DIR / "restoration_plan.json"
        assert plan_path.exists(), "restoration_plan.json was not written"
        plan = _load_plan()
        assert isinstance(plan.get("assignments"), list)
        assert plan["assignments"], "the plan must restore at least one feeder"
        for row in plan["assignments"]:
            assert set(row) == {"feeder_id", "island_id"}
            assert isinstance(row["feeder_id"], str)
            assert isinstance(row["island_id"], str)


class TestIslandOperatingRules:
    def test_plan_satisfies_capacity_floor_and_resonance_rules(self):
        """The selected feeders must satisfy every island rule reported by the scorer."""
        result = evaluate(INPUT_DIR, OUTPUT_DIR)
        assert result.get("violations") == []
        assert result["critical_spread_score"] == 1.0
        assert result["district_coverage_score"] == 1.0
        plan = _load_plan()
        rows = plan["assignments"]
        feeder_ids = [row["feeder_id"] for row in rows]
        assert len(feeder_ids) == len(set(feeder_ids))
        with open(INPUT_DIR / "feeders.jsonl", encoding="utf-8") as fh:
            feeders = {json.loads(line)["id"]: json.loads(line) for line in fh if line.strip()}
        by_island = {}
        for row in rows:
            by_island.setdefault(row["island_id"], []).append(feeders[row["feeder_id"]])
        for island_id, local in by_island.items():
            for idx, left in enumerate(local):
                for right in local[idx + 1 :]:
                    assert microgrid_resonance_index(left, right, island_id) > 1


class TestMicrogridScoreGate:
    def test_base_and_strict_scores_clear_the_required_thresholds(self):
        """The restored value must clear both the base score and stricter balance checks."""
        base = evaluate(INPUT_DIR, OUTPUT_DIR)
        strict = strict_evaluate(INPUT_DIR, OUTPUT_DIR)
        assert base["total_score"] >= 0.98
        assert strict["total_score_strict"] >= 0.96
        assert base["load_balance_score"] >= 0.32


class TestCompiledPlannerBehavior:
    def test_binary_regenerates_the_plan_and_handles_a_changed_config(self):
        """The compiled Go program must produce fresh feasible output for a modified policy."""
        assert BINARY.exists(), "expected compiled binary at /app/task_file/microgrid_restorer"
        assert os.access(BINARY, os.X_OK), "compiled binary is not executable"
        assert BINARY.read_bytes()[:4] == b"\x7fELF"

        base_plan = OUTPUT_DIR / "restoration_plan.json"
        if base_plan.exists():
            base_plan.unlink()
        subprocess.run([str(BINARY), str(INPUT_DIR), str(OUTPUT_DIR)], check=True, timeout=20)
        assert evaluate(INPUT_DIR, OUTPUT_DIR)["total_score"] >= 0.92

        with tempfile.TemporaryDirectory() as tmp:
            alt_input = Path(tmp) / "input"
            alt_output = Path(tmp) / "output"
            shutil.copytree(INPUT_DIR, alt_input)
            alt_output.mkdir()
            with open(alt_input / "config.json", encoding="utf-8") as fh:
                config = json.load(fh)
            config["mandatory_feeders"] = sorted(set(config["mandatory_feeders"]) | {"F06"})
            config["district_floor"]["water"] = 3
            with open(alt_input / "config.json", "w", encoding="utf-8") as fh:
                json.dump(config, fh, indent=2, sort_keys=True)
            subprocess.run([str(BINARY), str(alt_input), str(alt_output)], check=True, timeout=20)
            mutated = evaluate(alt_input, alt_output)
            mutated_strict = strict_evaluate(alt_input, alt_output)
            assert mutated.get("violations") == []
            assert mutated["total_score"] >= 0.95
            assert mutated_strict["total_score_strict"] >= 0.93
