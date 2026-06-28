import json
import subprocess
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

OUTPUT = Path("/app/output/report.json")
SCENARIOS = Path("/app/environment/data/scenarios.json")


def bundled_scenario_rows() -> list[dict]:
    return json.loads(SCENARIOS.read_text(encoding="utf-8"))


def canonicalize_depth_seed(seed: str) -> str:
    base = seed[: -len("-stale")] if seed.endswith("-stale") else seed
    if base.startswith("rev-"):
        return base
    return f"rev-{base}"


def expected_reload(row: dict) -> tuple[str, bool]:
    ack = bool(row.get("primary_unit")) and int(row.get("rev_hint", 0)) > 0
    dependent_fresh = (
        ack
        and bool(row.get("has_dependency_refresh"))
        and bool(row.get("has_chain_propagation"))
    )
    return "success", dependent_fresh


def expected_inactive_branch_fresh(row: dict) -> bool:
    return bool(row.get("inactive_branch_seen")) and bool(
        row.get("inactive_branch_refreshable")
    )


def expected_depth_revision(
    row: dict, dependent_fresh: bool, inactive_branch_fresh: bool
) -> str:
    tagged = canonicalize_depth_seed(str(row["depth_seed"]))
    if dependent_fresh and inactive_branch_fresh:
        return f"{tagged}-d{int(row['depth_steps'])}"
    return "rev-fallback-d0"


def expected_status_color(dependent_fresh: bool, inactive_branch_fresh: bool) -> str:
    if dependent_fresh and inactive_branch_fresh:
        return "green"
    return "amber"


def expected_row_output(row: dict) -> dict:
    reload_result, dependent_fresh = expected_reload(row)
    inactive_branch_fresh = expected_inactive_branch_fresh(row)
    return {
        "scenario": row["scenario"],
        "reload_result": reload_result,
        "dependent_fresh": dependent_fresh,
        "inactive_branch_fresh": inactive_branch_fresh,
        "depth_revision": expected_depth_revision(
            row, dependent_fresh, inactive_branch_fresh
        ),
        "status_color": expected_status_color(dependent_fresh, inactive_branch_fresh),
    }


def row_is_healthy(row: dict) -> bool:
    return (
        row["reload_result"] == "success"
        and row["dependent_fresh"]
        and row["inactive_branch_fresh"]
        and row["status_color"] == "green"
    )


def assert_report_matches_rows(report: dict, rows: list[dict]) -> None:
    scenarios = idx(report)
    assert {row["scenario"] for row in rows} == set(scenarios.keys())
    for row in rows:
        sid = row["scenario"]
        want = expected_row_output(row)
        got = scenarios[sid]
        for key, value in want.items():
            assert got[key] == value, f"{sid}.{key}: got {got[key]!r}, want {value!r}"
    healthy = sum(1 for r in report["scenarios"] if row_is_healthy(r))
    assert report["summary"]["healthy_count"] == healthy
    assert report["summary"]["stale_count"] == len(report["scenarios"]) - healthy


def load_report() -> dict:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "cargo",
            "run",
            "--manifest-path",
            "/app/environment/Cargo.toml",
            "--quiet",
            "--offline",
        ],
        check=True,
    )
    return json.loads(OUTPUT.read_text(encoding="utf-8"))


def idx(report: dict) -> dict:
    return {row["scenario"]: row for row in report["scenarios"]}


@contextmanager
def temporary_scenarios(rows: list[dict]):
    original = SCENARIOS.read_text(encoding="utf-8")
    try:
        SCENARIOS.write_text(json.dumps(rows), encoding="utf-8")
        yield rows
    finally:
        SCENARIOS.write_text(original, encoding="utf-8")


def test_bundled_scenarios_match_full_spec():
    """Default scenario bundle must satisfy every computed field and summary counter."""
    rows = bundled_scenario_rows()
    report = load_report()
    assert_report_matches_rows(report, rows)
    assert report["summary"]["healthy_count"] == len(rows)
    assert report["summary"]["stale_count"] == 0


def test_empty_primary_unit_blocks_dependent_freshness():
    """Dependent freshness requires a non-empty primary unit name."""
    rows = deepcopy(bundled_scenario_rows())
    target = next(r for r in rows if r["scenario"] == "alpha_active")
    target["primary_unit"] = ""
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        row = idx(report)["alpha_active"]
        assert row["dependent_fresh"] is False
        assert row["depth_revision"] == "rev-fallback-d0"
        assert row["status_color"] == "amber"


def test_zero_rev_hint_blocks_dependent_freshness():
    """A zero rev hint must surface as unhealthy even when graph flags are set."""
    rows = deepcopy(bundled_scenario_rows())
    target = next(r for r in rows if r["scenario"] == "gamma_multi_depth")
    target["rev_hint"] = 0
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        row = idx(report)["gamma_multi_depth"]
        assert row["dependent_fresh"] is False
        assert row["status_color"] == "amber"
        assert report["summary"]["stale_count"] >= 1


def test_missing_dependency_refresh_breaks_dependent_freshness():
    """Clearing dependency refresh must drop dependent freshness for that row only."""
    rows = deepcopy(bundled_scenario_rows())
    target = next(r for r in rows if r["scenario"] == "beta_inactive_branch")
    target["has_dependency_refresh"] = False
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        row = idx(report)["beta_inactive_branch"]
        assert row["dependent_fresh"] is False
        assert row["inactive_branch_fresh"] is True
        assert row["depth_revision"] == "rev-fallback-d0"
        assert idx(report)["alpha_active"]["dependent_fresh"] is True


def test_missing_chain_propagation_breaks_dependent_freshness():
    """Chain propagation is required for dependent freshness."""
    rows = deepcopy(bundled_scenario_rows())
    target = next(r for r in rows if r["scenario"] == "alpha_active")
    target["has_chain_propagation"] = False
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        assert idx(report)["alpha_active"]["dependent_fresh"] is False


def test_inactive_branch_requires_both_seen_and_refreshable():
    """Inactive-branch freshness needs both indicators; missing either one fails."""
    rows = deepcopy(bundled_scenario_rows())
    seen_only = next(r for r in rows if r["scenario"] == "beta_inactive_branch")
    seen_only["inactive_branch_refreshable"] = False
    refresh_only = next(r for r in rows if r["scenario"] == "gamma_multi_depth")
    refresh_only["inactive_branch_seen"] = False
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        assert idx(report)["beta_inactive_branch"]["inactive_branch_fresh"] is False
        assert idx(report)["gamma_multi_depth"]["inactive_branch_fresh"] is False


def test_status_tint_green_only_when_both_freshness_flags_true():
    """Status tint must be healthy only when dependent and inactive branch are both fresh."""
    rows = deepcopy(bundled_scenario_rows())
    target = next(r for r in rows if r["scenario"] == "beta_inactive_branch")
    target["inactive_branch_refreshable"] = False
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        row = idx(report)["beta_inactive_branch"]
        assert row["dependent_fresh"] is True
        assert row["inactive_branch_fresh"] is False
        assert row["status_color"] == "amber"


def test_depth_revision_appends_steps_only_when_fully_fresh():
    """Depth revision must append -dN only when both freshness flags are positive."""
    rows = deepcopy(bundled_scenario_rows())
    alpha = next(r for r in rows if r["scenario"] == "alpha_active")
    alpha["depth_steps"] = 9
    beta = next(r for r in rows if r["scenario"] == "beta_inactive_branch")
    beta["inactive_branch_refreshable"] = False
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        assert idx(report)["alpha_active"]["depth_revision"].endswith("-d9")
        assert idx(report)["beta_inactive_branch"]["depth_revision"] == "rev-fallback-d0"


def test_depth_seed_strips_stale_suffix_and_adds_prefix():
    """Bare seeds with a stale suffix must canonicalize to live rev- tokens without -stale."""
    rows = deepcopy(bundled_scenario_rows())
    alpha = next(r for r in rows if r["scenario"] == "alpha_active")
    alpha["depth_seed"] = "2026-05-stale"
    beta = next(r for r in rows if r["scenario"] == "beta_inactive_branch")
    beta["depth_seed"] = "beta-depth-stale"
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        for row in report["scenarios"]:
            assert row["depth_revision"].startswith("rev-")
            assert not row["depth_revision"].endswith("-stale")
            assert "rev-rev-" not in row["depth_revision"]


def test_depth_seed_with_existing_rev_prefix_not_doubled():
    """Seeds that already carry rev- must not be prefixed twice after stale stripping."""
    rows = deepcopy(bundled_scenario_rows())
    gamma = next(r for r in rows if r["scenario"] == "gamma_multi_depth")
    gamma["depth_seed"] = "rev-2026-05-stale"
    gamma["depth_steps"] = 6
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        got = idx(report)["gamma_multi_depth"]["depth_revision"]
        assert got == "rev-2026-05-d6"
        assert "rev-rev-" not in got


def test_depth_steps_change_recomputes_revision_suffix():
    """Mutating depth_steps must change the emitted -dN suffix for a fresh row."""
    rows = deepcopy(bundled_scenario_rows())
    alpha = next(r for r in rows if r["scenario"] == "alpha_active")
    alpha["depth_steps"] = 11
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        assert idx(report)["alpha_active"]["depth_revision"].endswith("-d11")


def test_added_scenario_row_is_computed_not_hardcoded():
    """Inserting a fourth scenario must produce a fourth output row with spec-correct fields."""
    rows = deepcopy(bundled_scenario_rows())
    rows.append(
        {
            "scenario": "delta_edge",
            "primary_unit": "node-d",
            "rev_hint": 2,
            "has_dependency_refresh": True,
            "has_chain_propagation": True,
            "inactive_branch_seen": False,
            "inactive_branch_refreshable": True,
            "depth_seed": "delta-seed",
            "depth_steps": 1,
        }
    )
    with temporary_scenarios(rows):
        report = load_report()
        assert len(report["scenarios"]) == 4
        assert_report_matches_rows(report, rows)
        assert idx(report)["delta_edge"]["inactive_branch_fresh"] is False


def test_removed_scenario_shrinks_report():
    """Dropping a scenario from input must remove it from the regenerated report."""
    rows = [r for r in bundled_scenario_rows() if r["scenario"] != "gamma_multi_depth"]
    with temporary_scenarios(rows):
        report = load_report()
        assert len(report["scenarios"]) == 2
        assert "gamma_multi_depth" not in idx(report)
        assert_report_matches_rows(report, rows)


def test_multi_row_mutations_keep_per_scenario_isolation():
    """Independent mutations on two rows must not bleed into untouched scenarios."""
    rows = deepcopy(bundled_scenario_rows())
    alpha = next(r for r in rows if r["scenario"] == "alpha_active")
    alpha["rev_hint"] = 0
    gamma = next(r for r in rows if r["scenario"] == "gamma_multi_depth")
    gamma["inactive_branch_seen"] = False
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        assert idx(report)["beta_inactive_branch"]["status_color"] == "green"
        assert idx(report)["alpha_active"]["dependent_fresh"] is False
        assert idx(report)["gamma_multi_depth"]["inactive_branch_fresh"] is False


def test_summary_stale_count_tracks_unhealthy_rows():
    """Summary stale_count must equal rows that are not fully healthy."""
    rows = deepcopy(bundled_scenario_rows())
    for row in rows:
        row["has_chain_propagation"] = False
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        assert report["summary"]["healthy_count"] == 0
        assert report["summary"]["stale_count"] == len(rows)


def test_low_rev_hint_still_allows_freshness_when_positive():
    """Small positive rev hints must not be treated as stale by an arbitrary threshold."""
    rows = deepcopy(bundled_scenario_rows())
    target = next(r for r in rows if r["scenario"] == "alpha_active")
    target["rev_hint"] = 1
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        assert idx(report)["alpha_active"]["dependent_fresh"] is True


def test_depth_revision_fallback_when_only_dependent_fresh():
    """Dependent-only freshness must still emit the fallback depth token."""
    rows = deepcopy(bundled_scenario_rows())
    target = next(r for r in rows if r["scenario"] == "gamma_multi_depth")
    target["inactive_branch_seen"] = False
    target["inactive_branch_refreshable"] = False
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        row = idx(report)["gamma_multi_depth"]
        assert row["dependent_fresh"] is True
        assert row["inactive_branch_fresh"] is False
        assert row["depth_revision"] == "rev-fallback-d0"


def test_depth_revision_fallback_when_only_inactive_branch_fresh():
    """Inactive-only freshness must not append -dN without dependent freshness."""
    rows = deepcopy(bundled_scenario_rows())
    target = next(r for r in rows if r["scenario"] == "alpha_active")
    target["rev_hint"] = 0
    target["has_dependency_refresh"] = False
    target["has_chain_propagation"] = False
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        row = idx(report)["alpha_active"]
        assert row["dependent_fresh"] is False
        assert row["inactive_branch_fresh"] is True
        assert row["depth_revision"] == "rev-fallback-d0"
        assert row["status_color"] == "amber"


def test_scenario_order_follows_input_file():
    """Output row order must follow scenarios.json order, not a hardcoded sort."""
    rows = deepcopy(bundled_scenario_rows())
    rows.reverse()
    with temporary_scenarios(rows):
        report = load_report()
        assert [r["scenario"] for r in report["scenarios"]] == [
            r["scenario"] for r in rows
        ]
        assert_report_matches_rows(report, rows)


def test_zero_depth_steps_still_formats_suffix():
    """depth_steps of zero must still produce a -d0 suffix when fully fresh."""
    rows = deepcopy(bundled_scenario_rows())
    target = next(r for r in rows if r["scenario"] == "beta_inactive_branch")
    target["depth_steps"] = 0
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        assert idx(report)["beta_inactive_branch"]["depth_revision"].endswith("-d0")


def test_reload_result_stays_success_while_graph_is_unhealthy():
    """Unhealthy graph rows must still keep the existing reload success label."""
    rows = deepcopy(bundled_scenario_rows())
    target = next(r for r in rows if r["scenario"] == "alpha_active")
    target["has_chain_propagation"] = False
    with temporary_scenarios(rows):
        report = load_report()
        assert_report_matches_rows(report, rows)
        assert idx(report)["alpha_active"]["reload_result"] == "success"
