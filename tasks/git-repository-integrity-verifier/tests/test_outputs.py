"""Verifier for git-repository-integrity-verifier."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest

from reference_solver import compute_expected, load_json

APP = Path("/app")
DATA = APP / "data"

(
    EXPECTED_DIVERGENCE,
    EXPECTED_ORPHANS,
    EXPECTED_REPORT,
    EXPECTED_HISTORY,
) = compute_expected()

REPO_ID = load_json("repository_metadata.json")["repository_id"]
POLICY = load_json("integrity_policy.json")
REPORT_CFG = POLICY["outputs"]["repository_integrity_report"]
HISTORY_CFG = POLICY["outputs"]["history_reconstruction"]


def report_cfg_line(key: str, **kwargs: object) -> str:
    template = REPORT_CFG["repository_summary_lines"][key]
    return template.format(**kwargs)


def metric_cfg_line(key: str, **kwargs: object) -> str:
    return REPORT_CFG["metric_line_templates"][key].format(**kwargs)


def read_text(name: str) -> str:
    return (APP / name).read_text(encoding="utf-8")


def read_json(name: str) -> dict:
    return json.loads((APP / name).read_text(encoding="utf-8"))


# --- output presence ---


def test_repository_integrity_report_exists() -> None:
    assert (APP / "repository_integrity_report.md").is_file()


def test_branch_divergence_exists() -> None:
    assert (APP / "branch_divergence.json").is_file()


def test_orphan_commits_exists() -> None:
    assert (APP / "orphan_commits.json").is_file()


def test_history_reconstruction_exists() -> None:
    assert (APP / "history_reconstruction.md").is_file()


def test_integrity_policy_present() -> None:
    assert (DATA / "integrity_policy.json").is_file()


def test_commit_graph_present() -> None:
    assert (DATA / "commit_graph.json").is_file()


# --- branch_divergence.json schema ---


def test_divergence_top_level_keys() -> None:
    doc = read_json("branch_divergence.json")
    assert set(doc.keys()) == set(POLICY["outputs"]["branch_divergence"]["keys"])


def test_divergence_repository_id() -> None:
    assert read_json("branch_divergence.json")["repository_id"] == REPO_ID


def test_divergence_pair_count() -> None:
    pairs = read_json("branch_divergence.json")["pairs"]
    branches = load_json("branch_refs.json")["branches"]
    expected_pairs = len(branches) * (len(branches) - 1) // 2
    assert len(pairs) == expected_pairs


def test_divergence_pair_entry_fields() -> None:
    required = set(POLICY["outputs"]["branch_divergence"]["pair_entry_keys"])
    for entry in read_json("branch_divergence.json")["pairs"]:
        assert set(entry.keys()) == required


def test_divergence_pairs_sorted() -> None:
    pairs = read_json("branch_divergence.json")["pairs"]
    observed = [(p["branch_a"], p["branch_b"]) for p in pairs]
    assert observed == sorted(observed)


def test_divergence_matches_reference() -> None:
    assert read_json("branch_divergence.json") == EXPECTED_DIVERGENCE


def test_main_release_divergence_total() -> None:
    pairs = {(p["branch_a"], p["branch_b"]): p for p in read_json("branch_divergence.json")["pairs"]}
    expected = next(
        row
        for row in EXPECTED_DIVERGENCE["pairs"]
        if row["branch_a"] == "main" and row["branch_b"] == "release"
    )
    row = pairs[("main", "release")]
    assert row["ahead_a"] == expected["ahead_a"]
    assert row["ahead_b"] == expected["ahead_b"]
    assert row["divergence_total"] == expected["divergence_total"]


# --- orphan_commits.json ---


def test_orphan_top_level_keys() -> None:
    doc = read_json("orphan_commits.json")
    assert set(doc.keys()) == set(POLICY["outputs"]["orphan_commits"]["keys"])


def test_orphan_count_matches_list() -> None:
    doc = read_json("orphan_commits.json")
    assert doc["count"] == len(doc["orphans"])


def test_orphan_entry_fields() -> None:
    required = set(POLICY["outputs"]["orphan_commits"]["orphan_entry_keys"])
    for entry in read_json("orphan_commits.json")["orphans"]:
        assert set(entry.keys()) == required


def test_orphan_sha_sorted() -> None:
    shas = [row["sha"] for row in read_json("orphan_commits.json")["orphans"]]
    assert shas == sorted(shas)


def test_orphan_matches_reference() -> None:
    assert read_json("orphan_commits.json") == EXPECTED_ORPHANS


def test_orphan_count_is_three() -> None:
    assert read_json("orphan_commits.json")["count"] == 3


def test_orphan_reasons_include_rebase_and_amend() -> None:
    reasons = {row["orphan_reason"] for row in read_json("orphan_commits.json")["orphans"]}
    assert "rebase_superseded" in reasons
    assert "amend_superseded" in reasons


def test_amended_hotfix_orphan_subject() -> None:
    orphans = read_json("orphan_commits.json")["orphans"]
    amended = [row for row in orphans if row["orphan_reason"] == "amend_superseded"]
    assert len(amended) == 1
    assert amended[0]["subject"] == "fix: critical patch"


# --- repository_integrity_report.md ---


def test_report_required_sections() -> None:
    body = read_text("repository_integrity_report.md")
    for section in POLICY["outputs"]["repository_integrity_report"]["required_sections"]:
        assert f"## {section}" in body


def test_report_title_matches_policy() -> None:
    expected = REPORT_CFG["title_template"].format(repository_id=REPO_ID)
    assert read_text("repository_integrity_report.md").splitlines()[0] == expected


def test_report_repository_id_line() -> None:
    assert report_cfg_line("repository_id", repository_id=REPO_ID) in read_text(
        "repository_integrity_report.md"
    )


def test_report_graph_integrity_score() -> None:
    expected = next(
        line for line in EXPECTED_REPORT.splitlines() if line.startswith("- graph_integrity_score:")
    )
    assert expected in read_text("repository_integrity_report.md")


def test_report_merge_consistency_score() -> None:
    expected = next(
        line for line in EXPECTED_REPORT.splitlines() if line.startswith("- merge_consistency_score:")
    )
    assert expected in read_text("repository_integrity_report.md")


def test_report_orphan_count_line() -> None:
    expected = metric_cfg_line("orphan_commit_count", count=EXPECTED_ORPHANS["count"])
    assert expected in read_text("repository_integrity_report.md")


def test_report_branch_pair_count() -> None:
    expected = metric_cfg_line("branch_pair_count", count=len(EXPECTED_DIVERGENCE["pairs"]))
    assert expected in read_text("repository_integrity_report.md")


def test_report_merge_findings_clean() -> None:
    assert REPORT_CFG["merge_findings_clean_line"] in read_text("repository_integrity_report.md")


def test_report_orphan_summary_lines_from_policy() -> None:
    report = read_text("repository_integrity_report.md")
    template = REPORT_CFG["orphan_entry_line_template"]
    sha_len = REPORT_CFG["sha_short_length"]
    for orphan in read_json("orphan_commits.json")["orphans"]:
        expected = template.format(
            sha_short=orphan["sha"][:sha_len],
            subject=orphan["subject"],
            orphan_reason=orphan["orphan_reason"],
        )
        assert expected in report


# --- history_reconstruction.md ---


def test_history_title() -> None:
    expected = HISTORY_CFG["title_template"].format(repository_id=REPO_ID)
    assert read_text("history_reconstruction.md").splitlines()[0] == expected


def test_history_contains_merge_event() -> None:
    assert "merge feature/auth" in read_text("history_reconstruction.md")


def test_history_contains_cherry_pick() -> None:
    assert "cherry-pick" in read_text("history_reconstruction.md")


def test_history_contains_rebase_finish() -> None:
    assert "rebase (finish)" in read_text("history_reconstruction.md")


def test_history_contains_amend() -> None:
    assert "commit (amend)" in read_text("history_reconstruction.md")


def test_history_lines_use_policy_template() -> None:
    for line in read_text("history_reconstruction.md").splitlines():
        if not line.startswith("- "):
            continue
        assert ": " in line
        head, summary = line.split(": ", 1)
        assert summary
        author_date, ref = head[2:].split(" ", 1)
        assert author_date
        assert ref.startswith("refs/")


def test_history_event_count_matches_reference() -> None:
    expected_count = sum(1 for line in EXPECTED_HISTORY.splitlines() if line.startswith("- "))
    actual_count = sum(1 for line in read_text("history_reconstruction.md").splitlines() if line.startswith("- "))
    assert actual_count == expected_count


def test_history_events_sorted_by_date() -> None:
    lines = [
        line
        for line in read_text("history_reconstruction.md").splitlines()
        if line.startswith("- 2025-")
    ]
    dates = [line.split()[1] for line in lines]
    assert dates == sorted(dates)


# --- determinism ---


def test_rerun_produces_identical_divergence() -> None:
    solve = APP / "solution" / "solve.sh"
    if not solve.is_file():
        pytest.skip("oracle solve.sh not mounted")
    before = (APP / "branch_divergence.json").read_bytes()
    subprocess.run(["bash", str(solve)], check=True)
    after = (APP / "branch_divergence.json").read_bytes()
    assert before == after


def test_orphan_discovered_via_ref_format() -> None:
    pattern = re.compile(r"^refs/heads/")
    for row in read_json("orphan_commits.json")["orphans"]:
        assert pattern.match(row["discovered_via_ref"])
