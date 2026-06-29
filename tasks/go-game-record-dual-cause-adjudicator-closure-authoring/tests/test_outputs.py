import json
import os
import re
import shutil
import subprocess
from pathlib import Path

APP_DIR = Path(os.environ.get("APP_DIR", "/app"))


def run_cmd(command, *, cwd=APP_DIR, check=True):
    env = os.environ.copy()
    env.setdefault("GOCACHE", str(APP_DIR / ".gocache"))
    env.setdefault("GOMODCACHE", str(APP_DIR / ".gomodcache"))
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if check and result.returncode != 0:
        raise AssertionError(
            f"command failed: {' '.join(command)}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def sha256(path: Path) -> str:
    result = subprocess.run(["sha256sum", str(path)], text=True, capture_output=True, check=True)
    return result.stdout.split()[0]


def regenerate() -> dict:
    output = APP_DIR / "output" / "adjudication-proof.json"
    if output.exists():
        output.write_text('{"schema_version":"stale"}\n', encoding="utf-8")
    run_cmd([str(APP_DIR / "tools" / "run_public_workflow.sh")])
    assert output.exists(), "public workflow did not create adjudication-proof.json"
    return json.loads(output.read_text(encoding="utf-8"))


def by_id(report: dict, record_id: str) -> dict:
    records = {item["record_id"]: item for item in report["records"]}
    assert record_id in records, f"missing record {record_id}; saw {sorted(records)}"
    return records[record_id]


def test_public_workflow_regenerates_current_proof():
    """The visible workflow must overwrite stale output and emit current provenance."""
    report = regenerate()
    assert report["schema_version"] == "go-adjudication-proof-v1"
    assert report["all_records_agree"] is True
    assert report["rulebook"]["sha256"] == sha256(APP_DIR / "u" / "tournament_rulebook.json")
    assert report["policy"]["sha256"] == sha256(APP_DIR / "j" / "policy.json")
    for record_name in ["dragon-cup-17.ggr", "legacy-1999.ggr"]:
        path = APP_DIR / "r" / record_name
        found = [item for item in report["records"] if item["path_sha256"] == sha256(path)]
        assert found, f"no proof entry carries the current hash for {record_name}"


def test_dragon_variation_rollback_and_adjudicator_agreement():
    """Dragon Cup replay must close the review branch and match the independent decision."""
    report = regenerate()
    dragon = by_id(report, "dragon-cup-17")
    engine = dragon["rules_engine"]
    judge = dragon["independent_judge"]
    assert engine["winner"] == "B"
    assert engine["margin"] == 1.5
    assert engine["passes_to_close"] == 2
    assert engine["terminal_pass_move_numbers"] == [10, 11]
    assert judge["agrees_with_rules_engine"] is True
    assert judge["winner"] == engine["winner"]
    assert judge["margin"] == engine["margin"]
    variations = {item["name"]: item for item in engine["variation_replays"]}
    assert "ko-threat-read" in variations
    branch = variations["ko-threat-read"]
    assert branch["from_move"] == 4
    assert branch["branch_leak_count"] == 0
    assert set(branch["branch_only_moves"]) == {"B:E5", "W:D5"}
    assert branch["state_hash"] != engine["final_state_hash"]


def test_legacy_archive_score_notation_remains_accepted():
    """The old score-token record must survive the same replay and adjudication path."""
    report = regenerate()
    legacy = by_id(report, "sansei-legacy-1999")
    engine = legacy["rules_engine"]
    judge = legacy["independent_judge"]
    assert legacy["compatibility"]["legacy_score_notation"] is True
    assert engine["legacy_score_notation"] is True
    assert engine["winner"] == "B"
    assert engine["margin"] == 2.5
    assert engine["passes_to_close"] == 2
    assert judge["agrees_with_rules_engine"] is True
    assert judge["winner"] == "B"
    assert judge["margin"] == 2.5


def test_record_copy_with_same_contract_is_not_hardcoded(tmp_path):
    """A semantically identical Dragon record copy must be adjudicated from its own bytes."""
    source = APP_DIR / "r" / "dragon-cup-17.ggr"
    clone = tmp_path / "dragon-copy.ggr"
    text = source.read_text(encoding="utf-8")
    assert re.search(r"^record_id: dragon-cup-17$", text, flags=re.MULTILINE)
    clone.write_text(
        text.replace("record_id: dragon-cup-17", "record_id: dragon-cup-17-copy")
        + "\n# archive copy with identical move semantics\n",
        encoding="utf-8",
    )
    out = tmp_path / "copy-proof.json"
    run_cmd(
        [
            "go",
            "run",
            "./cmd/goadj",
            "--rulebook",
            "u/tournament_rulebook.json",
            "--policy",
            "j/policy.json",
            "--record",
            str(clone),
            "--legacy",
            "r/legacy-1999.ggr",
            "--out",
            str(out),
        ]
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    clone_entry = by_id(report, "dragon-cup-17-copy")
    assert clone_entry["path_sha256"] == sha256(clone)
    assert clone_entry["rules_engine"]["winner"] == "B"
    assert clone_entry["rules_engine"]["margin"] == 1.5


def test_deleting_generated_state_does_not_replace_authorities(tmp_path):
    """Removing output/cache directories must not be enough unless source authorities agree."""
    shutil.rmtree(APP_DIR / "output", ignore_errors=True)
    shutil.rmtree(APP_DIR / ".gocache", ignore_errors=True)
    report = regenerate()
    dragon = by_id(report, "dragon-cup-17")
    legacy = by_id(report, "sansei-legacy-1999")
    assert dragon["independent_judge"]["agrees_with_rules_engine"] is True
    assert legacy["independent_judge"]["agrees_with_rules_engine"] is True
