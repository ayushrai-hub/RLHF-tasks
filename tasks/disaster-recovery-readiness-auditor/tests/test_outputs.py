"""Verifier for disaster recovery readiness auditor."""
from __future__ import annotations

import json
import math
import re

from reference_solver import (
    APP,
    ASSESSMENT_DATE_UTC,
    BLOCKER_SOURCE_PRIORITY,
    EVIDENCE_PRIORITY,
    MONITORING_PROBE_RE,
    OUTPUT_SCHEMA,
    POLICY,
    POSTMORTEM_STEP_SOURCE,
    PRIMARY_BACKUP_REGIONS,
    RESTORE_CHECKPOINT_RE,
    backup_row_counts,
    build_gaps,
    build_rto_rpo_assessment,
    compute_expected,
    compute_readiness_score,
    iter_corpus_files,
    load_failover_blockers,
    load_scoped_systems,
    load_targets,
    manifest_qualifies,
    normalize_canonical,
    observed_rpo_for,
    observed_rto_for,
    replication_audited_for,
    replication_row_counts,
    restore_checkpoint_row_counts,
    rpo_evidence_for,
    rto_evidence_for,
    scan_lines,
    within_assessment_window,
)

(
    EXPECTED_ASSESSMENT,
    EXPECTED_GAPS,
    _EXPECTED_REPORT,
    EXPECTED_TIMELINE,
) = compute_expected()

BACKUP_RESULT_RE = re.compile(
    r"^BACKUP_RESULT (?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"(?P<system>\S+) (?P<region>\S+) (?P<status>success|failure|partial) "
    r"(?P<recovery>\d+) (?P<loss>\d+) (?P<source>\S+)$"
)
REPLICATION_LAG_RE = re.compile(
    r"^REPLICATION_LAG (?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"(?P<system>\S+) (?P<source_region>\S+) (?P<target_region>\S+) "
    r"(?P<lag>\d+) (?P<source>\S+)$"
)
RECOVERY_TEST_RE = re.compile(
    r"^RECOVERY_TEST (?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"(?P<system>\S+) (?P<status>passed|failed) "
    r"(?P<rto>\d+) (?P<rpo>\d+) (?P<source>\S+)$"
)
FAILOVER_STEP_RE = re.compile(
    r"^FAILOVER_STEP (?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"(?P<system>\S+) (?P<action>\S+) (?P<source_region>\S+) "
    r"(?P<target_region>\S+) (?P<elapsed>\d+) (?P<source>\S+)$"
)
RUNBOOK_STATUS_RE = re.compile(
    r"^RUNBOOK_STATUS (?P<system>\S+) (?P<status>current|outdated|missing|draft|superseded) "
    r"(?P<review>\S+) (?P<source>\S+)$"
)

SCOPED_SYSTEMS = {
    "analytics-pipeline",
    "cache-cluster",
    "identity-core",
    "notification-hub",
    "order-api",
    "payments-ledger",
    "search-index",
}


def load_assessment() -> dict:
    return json.loads((APP / "rto_rpo_assessment.json").read_text(encoding="utf-8"))


def load_gaps() -> dict:
    return json.loads((APP / "recovery_gaps.json").read_text(encoding="utf-8"))


def load_report() -> str:
    return (APP / "dr_readiness_report.md").read_text(encoding="utf-8")


def load_timeline() -> str:
    return (APP / "failover_timeline.md").read_text(encoding="utf-8")


def parse_timeline_rows(text: str) -> list[dict]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("|")]
    assert len(lines) >= 2
    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    rows: list[dict] = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) == len(headers):
            rows.append(dict(zip(headers, cells, strict=True)))
    return rows


def assessment_row(system: str) -> dict:
    return next(r for r in load_assessment()["systems"] if r["system"] == system)


# --- artifact presence ---


def test_dr_readiness_report_exists() -> None:
    assert (APP / "dr_readiness_report.md").is_file()


def test_rto_rpo_assessment_json_exists() -> None:
    assert (APP / "rto_rpo_assessment.json").is_file()


def test_recovery_gaps_json_exists() -> None:
    assert (APP / "recovery_gaps.json").is_file()


def test_failover_timeline_exists() -> None:
    assert (APP / "failover_timeline.md").is_file()


def test_handbook_exists() -> None:
    assert (APP / "architecture_docs" / "dr-readiness-handbook.md").is_file()


def test_compliance_policy_exists() -> None:
    assert (APP / "compliance_requirements" / "regional-failover-policy.md").is_file()


def test_dr_audit_policy_exists() -> None:
    assert (APP / "architecture_docs" / "dr-audit-policy.json").is_file()


# --- schema ---


def test_assessment_top_level_keys() -> None:
    assert set(load_assessment().keys()) == OUTPUT_SCHEMA["assessment_top_level_keys"]


def test_assessment_system_row_keys() -> None:
    required = OUTPUT_SCHEMA["system_row_keys"]
    for row in load_assessment()["systems"]:
        assert set(row.keys()) == required


def test_recovery_gaps_top_level_keys() -> None:
    assert set(load_gaps().keys()) == OUTPUT_SCHEMA["gaps_top_level_keys"]


def test_gap_entry_keys() -> None:
    required = OUTPUT_SCHEMA["gap_entry_keys"]
    for gap in load_gaps()["gaps"]:
        assert set(gap.keys()) == required


def test_runbook_issue_keys() -> None:
    required = OUTPUT_SCHEMA["runbook_issue_keys"]
    for issue in load_gaps()["runbook_issues"]:
        assert set(issue.keys()) == required


def test_failover_blocker_keys() -> None:
    required = OUTPUT_SCHEMA["failover_blocker_keys"]
    for blocker in load_gaps()["failover_blockers"]:
        assert set(blocker.keys()) == required


def test_timeline_separator_row_exact() -> None:
    lines = [ln.strip() for ln in load_timeline().splitlines() if ln.strip().startswith("|")]
    assert len(lines) >= 2
    assert lines[1] == OUTPUT_SCHEMA["timeline_separator"]


def test_timeline_table_columns() -> None:
    rows = parse_timeline_rows(load_timeline())
    assert rows
    assert set(rows[0].keys()) == OUTPUT_SCHEMA["timeline_columns"]


def test_assessment_minute_fields_are_integers() -> None:
    for row in load_assessment()["systems"]:
        for key in (
            "rto_target_minutes",
            "rpo_target_minutes",
            "observed_rto_minutes",
            "observed_rpo_minutes",
        ):
            assert isinstance(row[key], int)


def test_assessment_meets_fields_are_booleans() -> None:
    for row in load_assessment()["systems"]:
        assert isinstance(row["meets_rto"], bool)
        assert isinstance(row["meets_rpo"], bool)


def test_systems_sorted_by_name() -> None:
    names = [row["system"] for row in load_assessment()["systems"]]
    assert names == sorted(names)


# --- reference oracle ---


def test_assessment_matches_independent_reference() -> None:
    assert load_assessment() == EXPECTED_ASSESSMENT


def test_gaps_match_independent_reference() -> None:
    assert load_gaps() == EXPECTED_GAPS


def test_timeline_matches_independent_reference() -> None:
    assert load_timeline() == EXPECTED_TIMELINE


def test_deterministic_assessment_on_recompute() -> None:
    assert build_rto_rpo_assessment() == load_assessment()


def test_readiness_score_matches_formula() -> None:
    assert load_assessment()["readiness_score"] == compute_readiness_score()


def test_assessment_date_utc_exact() -> None:
    assert load_assessment()["assessment_date_utc"] == ASSESSMENT_DATE_UTC


# --- normalization ---


def test_normalize_canonical_strips_bullet_and_backticks() -> None:
    assert normalize_canonical("- `RUNBOOK_STATUS x current 2026-01-01 p`") == (
        "RUNBOOK_STATUS x current 2026-01-01 p"
    )


def test_template_format_lines_skipped_in_scan() -> None:
    scanned = {line for _, line, _ in scan_lines()}
    assert not any("<system>" in line for line in scanned)


# --- backup traps ---


def test_backup_rows_require_primary_region_filter() -> None:
    for _, line, _ in scan_lines():
        m = BACKUP_RESULT_RE.match(line)
        if not m or m.group("region") not in PRIMARY_BACKUP_REGIONS:
            continue
        if backup_row_counts(m):
            assert m.group("region") in PRIMARY_BACKUP_REGIONS


def test_backup_primary_region_alias_counts_in_failure_resolution() -> None:
    alias_failures = [
        line
        for _, line, _ in scan_lines()
        if (m := BACKUP_RESULT_RE.match(line))
        and m.group("system") == "payments-ledger"
        and m.group("region") == "us-east-1-primary"
        and m.group("status") == "failure"
    ]
    assert alias_failures
    row = assessment_row("payments-ledger")
    assert row["observed_rto_minutes"] == observed_rto_for("payments-ledger")
    assert row["observed_rto_minutes"] >= 50


def test_backup_rows_ignore_post_assessment_timestamps() -> None:
    for _, line, _ in scan_lines():
        m = BACKUP_RESULT_RE.match(line)
        if not m or within_assessment_window(m.group("ts")):
            continue
        assert not backup_row_counts(m)


def test_failure_only_backup_resolution_when_failure_exists() -> None:
    for system in (
        "identity-core",
        "analytics-pipeline",
        "order-api",
        "notification-hub",
        "payments-ledger",
    ):
        bad_rows = [
            m.group("status")
            for _, line, _ in scan_lines()
            if (m := BACKUP_RESULT_RE.match(line))
            and m.group("system") == system
            and backup_row_counts(m)
            and m.group("status") in {"failure", "partial"}
        ]
        assert bad_rows
        assert observed_rto_for(system) >= 0


def test_partial_backup_counts_as_failure_resolution() -> None:
    partial_rows = [
        line
        for _, line, _ in scan_lines()
        if (m := BACKUP_RESULT_RE.match(line))
        and m.group("system") == "order-api"
        and m.group("status") == "partial"
    ]
    assert partial_rows
    assert assessment_row("order-api")["observed_rto_minutes"] == observed_rto_for("order-api")
    assert assessment_row("order-api")["observed_rto_minutes"] == 70


def test_order_api_rto_evidence_from_partial_backup() -> None:
    gap = next(g for g in load_gaps()["gaps"] if g["system"] == "order-api" and g["gap_type"] == "rto_exceeded")
    assert gap["observed_minutes"] == 70
    assert gap["evidence_source"] == rto_evidence_for("order-api")
    assert "backup_logs" in gap["evidence_source"]


def test_corpus_contains_eu_west_decoy_backups() -> None:
    decoys = [
        line
        for _, line, _ in scan_lines()
        if (m := BACKUP_RESULT_RE.match(line))
        and m.group("region") == "eu-west-1"
        and m.group("status") == "failure"
    ]
    assert decoys


def test_corpus_contains_post_assessment_decoy_backups() -> None:
    decoys = [
        line
        for _, line, _ in scan_lines()
        if (m := BACKUP_RESULT_RE.match(line))
        and not within_assessment_window(m.group("ts"))
        and m.group("status") == "failure"
    ]
    assert decoys


# --- replication traps ---


def test_replication_lag_requires_eu_west_target_region() -> None:
    for _, line, _ in scan_lines():
        m = REPLICATION_LAG_RE.match(line)
        if not m or m.group("source_region") != "us-east-1":
            continue
        if replication_row_counts(m):
            assert m.group("target_region") == "eu-west-1"


def test_replication_lag_below_minimum_seconds_excluded() -> None:
    noise = [
        int(m.group("lag"))
        for _, line, _ in scan_lines()
        if (m := REPLICATION_LAG_RE.match(line))
        and m.group("system") == "order-api"
        and int(m.group("lag")) < 120
    ]
    assert noise == [90]
    assert observed_rpo_for("order-api") == assessment_row("order-api")["observed_rpo_minutes"]


def test_replication_lag_uses_ceiling_minutes() -> None:
    for _, line, _ in scan_lines():
        m = REPLICATION_LAG_RE.match(line)
        if not m or not replication_row_counts(m):
            continue
        lag_min = math.ceil(int(m.group("lag")) / 60)
        system = m.group("system")
        assert observed_rpo_for(system) >= lag_min


def test_payments_rpo_ignores_reverse_direction_replication_lag() -> None:
    reverse = [
        line
        for _, line, _ in scan_lines()
        if (m := REPLICATION_LAG_RE.match(line))
        and m.group("system") == "payments-ledger"
        and m.group("source_region") == "eu-west-1"
    ]
    assert reverse
    assert assessment_row("payments-ledger")["observed_rpo_minutes"] == observed_rpo_for(
        "payments-ledger"
    )


# --- recovery drill traps ---


def test_recovery_drill_failed_rows_only() -> None:
    for _, line, _ in scan_lines():
        m = RECOVERY_TEST_RE.match(line)
        if not m or m.group("status") != "passed":
            continue
        system = m.group("system")
        assert observed_rto_for(system) != int(m.group("rto")) or int(m.group("rto")) == 0


def test_cache_cluster_rto_from_failed_drill_not_backup_success() -> None:
    row = assessment_row("cache-cluster")
    assert row["observed_rto_minutes"] == observed_rto_for("cache-cluster")
    assert row["observed_rto_minutes"] == 18


# --- monitoring probe traps ---


def test_monitoring_probe_regional_failover_contributes_to_rto() -> None:
    row = assessment_row("search-index")
    assert row["observed_rto_minutes"] == observed_rto_for("search-index")
    assert row["observed_rto_minutes"] == 125
    assert row["meets_rto"] is False


def test_monitoring_probe_rehearsal_scenario_excluded_from_rto() -> None:
    rehearsal = [
        int(m.group("recovery"))
        for _, line, _ in scan_lines()
        if (m := MONITORING_PROBE_RE.match(line))
        and m.group("scenario") == "regional_failover_rehearsal"
    ]
    assert rehearsal == [300]
    assert observed_rto_for("analytics-pipeline") == 200


def test_monitoring_probe_synthetic_drill_excluded_from_rto() -> None:
    synthetic = [
        int(m.group("recovery"))
        for _, line, _ in scan_lines()
        if (m := MONITORING_PROBE_RE.match(line))
        and m.group("system") == "order-api"
        and m.group("scenario") == "synthetic_drill"
    ]
    assert synthetic == [200]
    assert observed_rto_for("order-api") == 70


def test_search_index_rto_gap_evidence_backup_wins_priority_tie() -> None:
    gap = next(
        g for g in load_gaps()["gaps"] if g["system"] == "search-index" and g["gap_type"] == "rto_exceeded"
    )
    assert gap["observed_minutes"] == 125
    assert gap["evidence_source"] == rto_evidence_for("search-index")
    assert "backup_logs" in gap["evidence_source"]
    assert "monitoring_exports" not in gap["evidence_source"]


# --- failover step traps ---


def test_failover_steps_limited_to_postmortem_source() -> None:
    for _, line, _ in scan_lines():
        m = FAILOVER_STEP_RE.match(line)
        if not m or m.group("source") == POSTMORTEM_STEP_SOURCE:
            continue
        assert observed_rto_for(m.group("system")) != int(m.group("elapsed"))


def test_failover_promote_requires_eu_west_target_region_for_rto() -> None:
    for _, line, _ in scan_lines():
        m = FAILOVER_STEP_RE.match(line)
        if not m or m.group("source") != POSTMORTEM_STEP_SOURCE:
            continue
        if m.group("action") not in {"promote_secondary", "flush_and_rebuild"}:
            continue
        if m.group("target_region") != "eu-west-1":
            assert int(m.group("elapsed")) <= observed_rto_for(m.group("system"))


def test_failover_steps_require_us_east_source_region_for_rto() -> None:
    for _, line, _ in scan_lines():
        m = FAILOVER_STEP_RE.match(line)
        if not m or m.group("source") != POSTMORTEM_STEP_SOURCE:
            continue
        if m.group("source_region") != "us-east-1" and m.group("action") in {
            "promote_secondary",
            "flush_and_rebuild",
        }:
            assert int(m.group("elapsed")) <= observed_rto_for(m.group("system"))


def test_wait_for_dependency_excluded_from_observed_rto_max() -> None:
    wait_steps = [
        int(m.group("elapsed"))
        for _, line, _ in scan_lines()
        if (m := FAILOVER_STEP_RE.match(line))
        and m.group("action") == "wait_for_dependency"
        and m.group("source") == POSTMORTEM_STEP_SOURCE
    ]
    assert wait_steps
    assert observed_rto_for("identity-core") != max(wait_steps)


def test_slack_failover_decoys_do_not_inflate_rto() -> None:
    for system in ("order-api", "analytics-pipeline", "payments-ledger"):
        assert observed_rto_for(system) == assessment_row(system)["observed_rto_minutes"]


def test_failover_promote_step_not_dominating_payments_rto() -> None:
    row = assessment_row("payments-ledger")
    assert row["observed_rto_minutes"] == observed_rto_for("payments-ledger")
    assert row["observed_rto_minutes"] == 55


def test_corpus_contains_failover_step_decoys_outside_postmortem() -> None:
    decoys = [
        line
        for _, line, _ in scan_lines()
        if line.startswith("FAILOVER_STEP ")
        and POSTMORTEM_STEP_SOURCE not in line
    ]
    assert decoys


# --- runbook traps ---


def test_notification_hub_superseded_last_wins_over_missing() -> None:
    issue = next(i for i in load_gaps()["runbook_issues"] if i["system"] == "notification-hub")
    assert issue["status"] == "superseded"
    assert issue["source_relpath"].startswith("compliance_requirements/")


def test_runbook_draft_status_included_in_issues() -> None:
    issues = load_gaps()["runbook_issues"]
    draft = next(i for i in issues if i["system"] == "analytics-pipeline")
    assert draft["status"] == "draft"


def test_runbook_issues_exclude_identity_after_compliance_clear() -> None:
    systems = {i["system"] for i in load_gaps()["runbook_issues"]}
    assert "identity-core" not in systems


def test_backtick_wrapped_runbook_status_rows_parsed() -> None:
    assert any(i["system"] == "notification-hub" for i in load_gaps()["runbook_issues"])


def test_runbook_issues_sorted_by_system() -> None:
    names = [i["system"] for i in load_gaps()["runbook_issues"]]
    assert names == sorted(names)


# --- target resolution ---


def test_critical_tier_uses_higher_rto_penalty_in_score() -> None:
    penalties = OUTPUT_SCHEMA["penalties"]
    assert penalties["rto_failure_critical"] > penalties["rto_failure_standard"]
    assert load_assessment()["readiness_score"] == compute_readiness_score()


def test_payments_targets_use_compliance_not_architecture_decoy() -> None:
    row = assessment_row("payments-ledger")
    targets = load_targets()["payments-ledger"]
    assert row["rto_target_minutes"] == targets.rto_minutes == 15
    assert row["rpo_target_minutes"] == targets.rpo_minutes == 5


def test_late_compliance_target_last_wins_for_cache_rpo() -> None:
    row = assessment_row("cache-cluster")
    assert row["rpo_target_minutes"] == 1


def test_critical_tier_systems_present() -> None:
    tiers = {r["system"]: r["tier"] for r in load_assessment()["systems"]}
    assert tiers["cache-cluster"] == "critical"
    assert tiers["identity-core"] == "critical"
    assert tiers["payments-ledger"] == "critical"


def test_rpo_zero_target_requires_exact_zero_observed() -> None:
    for row in load_assessment()["systems"]:
        if row["rpo_target_minutes"] == 0:
            expected = row["observed_rpo_minutes"] == 0
        else:
            expected = row["observed_rpo_minutes"] <= row["rpo_target_minutes"]
        assert row["meets_rpo"] is expected


# --- gaps and blockers ---


def test_gaps_sorted_by_system_then_type() -> None:
    keys = [(g["system"], g["gap_type"]) for g in load_gaps()["gaps"]]
    assert keys == sorted(keys)


def test_gap_observed_matches_assessment() -> None:
    for gap in load_gaps()["gaps"]:
        row = assessment_row(gap["system"])
        if gap["gap_type"] == "rto_exceeded":
            assert gap["observed_minutes"] == row["observed_rto_minutes"]
            assert gap["target_minutes"] == row["rto_target_minutes"]
        else:
            assert gap["observed_minutes"] == row["observed_rpo_minutes"]
            assert gap["target_minutes"] == row["rpo_target_minutes"]


def test_gap_evidence_sources_are_documented_paths() -> None:
    corpus = {str(p.relative_to(APP)).replace("\\", "/") for p in iter_corpus_files()}
    for gap in load_gaps()["gaps"]:
        assert gap["evidence_source"] in corpus


def test_each_gap_evidence_source_matches_reference() -> None:
    ref_by_key = {(g["system"], g["gap_type"]): g for g in build_gaps()}
    for gap in load_gaps()["gaps"]:
        key = (gap["system"], gap["gap_type"])
        assert gap["evidence_source"] == ref_by_key[key]["evidence_source"]


def test_failover_blockers_exclude_draft_shard_blocked_step() -> None:
    systems = {b["system"] for b in load_gaps()["failover_blockers"]}
    assert "analytics-pipeline" not in systems


def test_failover_blockers_sorted_by_system_then_depends_on() -> None:
    keys = [(b["system"], b["depends_on"]) for b in load_gaps()["failover_blockers"]]
    assert keys == sorted(keys)


def test_search_index_blocker_uses_failover_dep_on_dedup() -> None:
    actual = next(b for b in load_gaps()["failover_blockers"] if b["system"] == "search-index")
    expected = next(b for b in load_failover_blockers() if b["system"] == "search-index")
    assert actual == expected
    assert "multi-region-topology" in actual["evidence_source"]
    assert POSTMORTEM_STEP_SOURCE not in actual["evidence_source"]


def test_gap_flag_rows_ignored_in_outputs() -> None:
    gap_types = {g["gap_type"] for g in load_gaps()["gaps"]}
    assert gap_types <= {"rto_exceeded", "rpo_exceeded"}


# --- timeline ---


def test_timeline_blocked_steps_use_zero_elapsed_minutes() -> None:
    for row in parse_timeline_rows(load_timeline()):
        if row["action"] == "blocked":
            assert row["elapsed_minutes"] == "0"


def test_timeline_includes_blocked_and_wait_steps() -> None:
    actions = {row["action"] for row in parse_timeline_rows(load_timeline())}
    assert "blocked" in actions
    assert "wait_for_dependency" in actions


def test_timeline_sorted_by_timestamp_then_system() -> None:
    rows = parse_timeline_rows(load_timeline())
    keys = [(r["ts_utc"], r["system"]) for r in rows]
    assert keys == sorted(keys)


def test_postmortem_failover_steps_require_backtick_normalization() -> None:
    rows = parse_timeline_rows(load_timeline())
    assert {r["source_relpath"] for r in rows} == {POSTMORTEM_STEP_SOURCE}


# --- report ---


def test_report_required_headings_in_order() -> None:
    text = load_report()
    positions = [text.index(h) for h in OUTPUT_SCHEMA["report_headings"]]
    assert positions == sorted(positions)


def test_report_sections_reference_assessment_and_gaps() -> None:
    text = load_report()
    assessment = load_assessment()
    gaps = load_gaps()
    assert assessment["assessment_date_utc"] in text
    assert str(assessment["readiness_score"]) in text
    for gap in gaps["gaps"]:
        assert gap["system"] in text
        assert gap["evidence_source"] in text
    for issue in gaps["runbook_issues"]:
        assert issue["system"] in text
        assert issue["source_relpath"] in text


def test_report_single_h1_title() -> None:
    h1_lines = [
        ln for ln in load_report().splitlines() if ln.startswith("# ") and not ln.startswith("## ")
    ]
    assert len(h1_lines) == 1
    assert h1_lines[0] == f"# {OUTPUT_SCHEMA['report_title']}"


def test_timeline_single_h1_title() -> None:
    h1_lines = [
        ln for ln in load_timeline().splitlines() if ln.startswith("# ") and not ln.startswith("## ")
    ]
    assert len(h1_lines) == 1
    assert h1_lines[0] == f"# {OUTPUT_SCHEMA['timeline_title']}"


def test_each_scoped_system_present_in_assessment() -> None:
    names = {row["system"] for row in load_assessment()["systems"]}
    assert names == SCOPED_SYSTEMS


# --- scoped-system gates ---


def test_settlement_router_excluded_without_manifest_inclusion() -> None:
    names = {row["system"] for row in load_assessment()["systems"]}
    assert "settlement-router" not in names
    decoy = [
        line
        for _, line, _ in scan_lines()
        if line.startswith("BACKUP_RESULT ") and "settlement-router" in line
    ]
    assert decoy


def test_scoped_systems_require_audit_scope_and_manifest() -> None:
    assert load_scoped_systems() == SCOPED_SYSTEMS


def test_manifest_audit_included_required_for_assessment() -> None:
    scoped = load_scoped_systems()
    for system in scoped:
        manifest = APP / "infrastructure_manifests" / f"{system}.json"
        assert manifest.is_file()
        doc = json.loads(manifest.read_text(encoding="utf-8"))
        assert manifest_qualifies(doc) is True


# --- critical tier grace ---


def test_identity_core_meets_rto_with_grace_but_strict_gap_emitted() -> None:
    row = assessment_row("identity-core")
    assert row["observed_rto_minutes"] == 32
    assert row["rto_target_minutes"] == 30
    assert row["meets_rto"] is True
    gap = next(
        g for g in load_gaps()["gaps"] if g["system"] == "identity-core" and g["gap_type"] == "rto_exceeded"
    )
    assert gap["observed_minutes"] == 32


def test_critical_grace_does_not_suppress_readiness_rto_penalty() -> None:
    row = assessment_row("identity-core")
    assert row["meets_rto"] is True
    assert row["observed_rto_minutes"] > row["rto_target_minutes"]


# --- restore checkpoint ---


def test_restore_checkpoint_failed_rows_contribute_to_rpo() -> None:
    rows = [
        line
        for _, line, _ in scan_lines()
        if RESTORE_CHECKPOINT_RE.match(line) and "analytics-pipeline" in line
    ]
    assert rows
    assert observed_rpo_for("analytics-pipeline") >= 450


def test_analytics_rpo_evidence_from_restore_checkpoint() -> None:
    gap = next(
        g for g in load_gaps()["gaps"] if g["system"] == "analytics-pipeline" and g["gap_type"] == "rpo_exceeded"
    )
    assert gap["observed_minutes"] == 450
    assert gap["evidence_source"] == rpo_evidence_for("analytics-pipeline")
    assert "q2-analytics-restore" in gap["evidence_source"]


def test_restore_checkpoint_passed_rows_ignored() -> None:
    for _, line, _ in scan_lines():
        m = RESTORE_CHECKPOINT_RE.match(line)
        if not m or m.group("status") != "passed":
            continue
        assert not restore_checkpoint_row_counts(m)


# --- evidence priority ---


def test_evidence_priority_table_in_schema() -> None:
    assert EVIDENCE_PRIORITY["BACKUP_RESULT"] > EVIDENCE_PRIORITY["MONITORING_PROBE"]
    assert EVIDENCE_PRIORITY["RESTORE_CHECKPOINT"] == EVIDENCE_PRIORITY["RECOVERY_TEST"]


def test_report_lists_strict_rto_gaps_not_meets_rto_only() -> None:
    text = load_report()
    row = assessment_row("identity-core")
    assert row["meets_rto"] is True
    assert "identity-core" in text
    gap = next(g for g in load_gaps()["gaps"] if g["system"] == "identity-core")
    assert gap["evidence_source"] in text


# --- policy gates ---


def test_policy_assessment_cycle_matches_manifests() -> None:
    cycle = POLICY["assessment_cycle"]
    for system in SCOPED_SYSTEMS:
        doc = json.loads((APP / "infrastructure_manifests" / f"{system}.json").read_text())
        assert doc[POLICY["manifest_gates"]["dr_audit_cycle_field"]] == cycle


def test_archival_warehouse_excluded_wrong_audit_cycle() -> None:
    names = {row["system"] for row in load_assessment()["systems"]}
    assert "archival-warehouse" not in names
    manifest = json.loads((APP / "infrastructure_manifests" / "archival-warehouse.json").read_text())
    assert manifest_qualifies(manifest) is False


def test_payments_replication_lag_ignored_when_not_audited() -> None:
    assert replication_audited_for("payments-ledger") is False
    qualifying = [
        line
        for _, line, _ in scan_lines()
        if (m := REPLICATION_LAG_RE.match(line))
        and m.group("system") == "payments-ledger"
        and replication_row_counts(m)
    ]
    assert qualifying == []
    row = assessment_row("payments-ledger")
    assert row["observed_rpo_minutes"] == observed_rpo_for("payments-ledger")


def test_blocker_source_priority_defined_in_policy() -> None:
    assert BLOCKER_SOURCE_PRIORITY["FAILOVER_DEP"] > BLOCKER_SOURCE_PRIORITY["FAILOVER_STEP_BLOCKED"]


def test_readiness_score_uses_combined_recovery_miss_cap() -> None:
    assert OUTPUT_SCHEMA["combined_recovery_miss"] is True
    dual_miss = [
        r["system"]
        for r in load_assessment()["systems"]
        if r["observed_rto_minutes"] > r["rto_target_minutes"] and not r["meets_rpo"]
    ]
    assert len(dual_miss) >= 2
    assert load_assessment()["readiness_score"] == compute_readiness_score()

