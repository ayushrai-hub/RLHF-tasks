import json
import subprocess
from pathlib import Path

REPORT = Path("/app/output/graph_report.json")
CHK = ["/app/bin/mgr_run", "--matrix", "--out", "/app/output/graph_report.json"]

REPEAT_PAIRS = (
    ("c0_base", "c0_repeat"),
    ("c1_var", "c1_repeat"),
    ("c2_var", "c2_repeat"),
)


def _prep() -> None:
    subprocess.run(["bash", "/app/environment/migrations/cln_m4.sh"], check=True)
    subprocess.run(["bash", "/app/environment/scripts/bake_m4.sh"], check=True)


def _arm(doc: dict, arm_id: str) -> dict:
    return next(a for a in doc["arms"] if a["arm_id"] == arm_id)


def _assert_repeat_pairs_match(doc: dict) -> None:
    for base_id, repeat_id in REPEAT_PAIRS:
        base = _arm(doc, base_id)
        repeat = _arm(doc, repeat_id)
        assert repeat["path_b_hex"] == base["path_b_hex"]
        assert repeat["cross_link"] == base["cross_link"]
        assert repeat["row_digest"] == base["row_digest"]


class TestMilestone3:
    def test_m3_second_pass_guard(self):
        """Repeat arms match paired arms within a run and run_token is stable across clean reruns."""
        _prep()
        subprocess.run(CHK, check=True)
        first = json.loads(REPORT.read_text(encoding="utf-8"))
        _assert_repeat_pairs_match(first)
        subprocess.run(["bash", "/app/environment/migrations/cln_m4.sh"], check=True)
        subprocess.run(CHK, check=True)
        second = json.loads(REPORT.read_text(encoding="utf-8"))
        _assert_repeat_pairs_match(second)
        assert first["run_token"] == second["run_token"]
        assert [a["row_digest"] for a in first["arms"]] == [a["row_digest"] for a in second["arms"]]

    def test_m3_no_prep_run_miss(self):
        """Second matrix invocation without cleanup exits non-zero after a successful first run."""
        _prep()
        subprocess.run(CHK, check=True)
        first = json.loads(REPORT.read_text(encoding="utf-8"))
        _assert_repeat_pairs_match(first)
        proc = subprocess.run(CHK, capture_output=True, text=True)
        assert proc.returncode != 0
