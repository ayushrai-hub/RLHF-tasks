#!/usr/bin/env python3
"""Reference DR readiness logic shared by oracle and verifier."""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

APP = Path("/app")
POLICY_PATH = APP / "architecture_docs/dr-audit-policy.json"


def load_dr_policy() -> dict:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


POLICY = load_dr_policy()
ASSESSMENT_DATE_UTC = POLICY["assessment_date_utc"]
POSTMORTEM_STEP_SOURCE = POLICY["outputs"]["failover_timeline"]["postmortem_source"]
PRIMARY_BACKUP_REGIONS = frozenset(POLICY["backup"]["primary_regions"])
BACKUP_FAILURE_STATUSES = frozenset(POLICY["backup"]["failure_statuses"])
REPLICATION_LAG_MIN_SECONDS = POLICY["replication"]["min_lag_seconds"]
EVIDENCE_PRIORITY = POLICY["evidence_priority"]
BLOCKER_SOURCE_PRIORITY = POLICY["blocker_source_priority"]
CRITICAL_RTO_GRACE = POLICY["critical_rto_grace_minutes"]
QUALIFYING_PROBE_SCENARIOS = frozenset(POLICY["monitoring_probe"]["qualifying_scenarios"])


def load_output_schema() -> dict:
    doc = POLICY
    o = doc["outputs"]
    report = o["dr_readiness_report"]
    timeline = o["failover_timeline"]
    return {
        "assessment_top_level_keys": set(o["rto_rpo_assessment"]["keys"]),
        "system_row_keys": set(o["rto_rpo_assessment"]["system_row_keys"]),
        "gaps_top_level_keys": set(o["recovery_gaps"]["keys"]),
        "gap_entry_keys": set(o["recovery_gaps"]["gap_entry_keys"]),
        "runbook_issue_keys": set(o["recovery_gaps"]["runbook_issue_keys"]),
        "failover_blocker_keys": set(o["recovery_gaps"]["failover_blocker_keys"]),
        "timeline_columns": set(timeline["columns"]),
        "timeline_separator": timeline["separator_row"],
        "report_title": report["title"],
        "timeline_title": timeline["title"],
        "report_headings": [f"## {h}" for h in report["headings"]],
        "penalties": doc["readiness_score"]["penalties"],
        "assessment_date_utc": doc["assessment_date_utc"],
        "combined_recovery_miss": doc["readiness_score"].get("combined_recovery_miss", False),
    }


OUTPUT_SCHEMA = load_output_schema()

CORPUS_DIRS = POLICY["corpus_scan_directories"]

RTO_TARGET_RE = re.compile(
    r"^RTO_TARGET (?P<system>\S+) (?P<minutes>\d+) (?P<tier>\S+) (?P<source>\S+)$"
)
RPO_TARGET_RE = re.compile(
    r"^RPO_TARGET (?P<system>\S+) (?P<minutes>\d+) (?P<tier>\S+) (?P<source>\S+)$"
)
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
RESTORE_CHECKPOINT_RE = re.compile(
    r"^RESTORE_CHECKPOINT (?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"(?P<system>\S+) (?P<status>passed|failed) "
    r"(?P<loss>\d+) (?P<source>\S+)$"
)
AUDIT_SCOPE_RE = re.compile(r"^AUDIT_SCOPE (?P<system>\S+) (?P<source>\S+)$")
RUNBOOK_STATUS_RE = re.compile(
    r"^RUNBOOK_STATUS (?P<system>\S+) (?P<status>current|outdated|missing|draft|superseded) "
    r"(?P<review>\S+) (?P<source>\S+)$"
)
MONITORING_PROBE_RE = re.compile(
    r"^MONITORING_PROBE (?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"(?P<system>\S+) (?P<scenario>\S+) (?P<recovery>\d+) (?P<source>\S+)$"
)
FAILOVER_DEP_RE = re.compile(
    r"^FAILOVER_DEP (?P<system>\S+) depends_on (?P<depends>\S+) "
    r"blocker_if_missing (?P<gate>\S+) (?P<source>\S+)$"
)
FAILOVER_STEP_RE = re.compile(
    r"^FAILOVER_STEP (?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"(?P<system>\S+) (?P<action>\S+) (?P<source_region>\S+) "
    r"(?P<target_region>\S+) (?P<elapsed>\d+) (?P<source>\S+)$"
)
FAILOVER_STEP_BLOCKED_RE = re.compile(
    r"^FAILOVER_STEP (?P<ts>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) "
    r"(?P<system>\S+) blocked (?P<depends>\S+) (?P<gate>\S+) (?P<source>\S+)$"
)


@dataclass(frozen=True)
class Target:
    system: str
    tier: str
    rto_minutes: int
    rpo_minutes: int


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


ASSESSMENT_TS = parse_ts(ASSESSMENT_DATE_UTC)


def within_assessment_window(ts: str) -> bool:
    return parse_ts(ts) <= ASSESSMENT_TS


def backup_row_counts(m: re.Match[str]) -> bool:
    return m.group("region") in PRIMARY_BACKUP_REGIONS and within_assessment_window(m.group("ts"))


def replication_row_counts(m: re.Match[str]) -> bool:
    return (
        m.group("source_region") == POLICY["replication"]["required_source_region"]
        and m.group("target_region") == POLICY["replication"]["required_target_region"]
        and int(m.group("lag")) >= REPLICATION_LAG_MIN_SECONDS
        and within_assessment_window(m.group("ts"))
        and replication_audited_for(m.group("system"))
    )


def monitoring_probe_row_counts(m: re.Match[str]) -> bool:
    return (
        m.group("scenario") in QUALIFYING_PROBE_SCENARIOS
        and within_assessment_window(m.group("ts"))
    )


def manifest_qualifies(doc: dict) -> bool:
    gates = POLICY["manifest_gates"]
    if doc.get(gates["audit_included_field"]) is not True:
        return False
    return doc.get(gates["dr_audit_cycle_field"]) == POLICY["assessment_cycle"]


def replication_audited_for(system: str) -> bool:
    path = APP / "infrastructure_manifests" / f"{system}.json"
    if not path.is_file():
        return False
    doc = json.loads(path.read_text(encoding="utf-8"))
    field = POLICY["manifest_gates"]["replication_audited_field"]
    return doc.get(field) is True


def recovery_test_row_counts(m: re.Match[str]) -> bool:
    return within_assessment_window(m.group("ts"))


def restore_checkpoint_row_counts(m: re.Match[str]) -> bool:
    return m.group("status") == "failed" and within_assessment_window(m.group("ts"))


def load_manifest_included() -> set[str]:
    included: set[str] = set()
    base = APP / "infrastructure_manifests"
    if base.is_dir():
        for path in sorted(base.glob("*.json")):
            doc = json.loads(path.read_text(encoding="utf-8"))
            if manifest_qualifies(doc):
                included.add(doc["system"])
    return included


def load_audit_scope_systems() -> set[str]:
    scope: set[str] = set()
    for _, line, _ in scan_lines():
        m = AUDIT_SCOPE_RE.match(line)
        if m:
            scope.add(m.group("system"))
    return scope


def load_scoped_systems() -> set[str]:
    return load_audit_scope_systems() & load_manifest_included()


def iter_corpus_files() -> list[Path]:
    files: list[Path] = []
    for sub in CORPUS_DIRS:
        base = APP / sub
        if base.is_dir():
            files.extend(sorted(base.rglob("*")))
    return [p for p in files if p.is_file()]


def rel(path: Path) -> str:
    return str(path.relative_to(APP)).replace("\\", "/")


def normalize_canonical(line: str) -> str:
    line = line.strip()
    if line.startswith("- "):
        line = line[2:].strip()
    if line.startswith("`") and "`" in line[1:]:
        line = line.strip("`")
    return line


def is_template_line(line: str) -> bool:
    return "<" in line and ">" in line


def scan_lines() -> list[tuple[str, str, int]]:
    rows: list[tuple[str, str, int]] = []
    prefixes = (
        "RTO_TARGET ",
        "RPO_TARGET ",
        "BACKUP_RESULT ",
        "REPLICATION_LAG ",
        "RECOVERY_TEST ",
        "RUNBOOK_STATUS ",
        "FAILOVER_DEP ",
        "FAILOVER_STEP ",
        "MONITORING_PROBE ",
        "RESTORE_CHECKPOINT ",
        "AUDIT_SCOPE ",
        "GAP_FLAG ",
    )
    for path in iter_corpus_files():
        r = rel(path)
        for idx, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            line = normalize_canonical(raw)
            if is_template_line(line):
                continue
            if line.startswith(prefixes):
                rows.append((r, line, idx))
    return rows


def load_targets() -> dict[str, Target]:
    rto: dict[str, tuple[int, str]] = {}
    rpo: dict[str, int] = {}
    for _, line, _ in scan_lines():
        m = RTO_TARGET_RE.match(line)
        if m:
            rto[m.group("system")] = (int(m.group("minutes")), m.group("tier"))
            continue
        m = RPO_TARGET_RE.match(line)
        if m:
            rpo[m.group("system")] = int(m.group("minutes"))
    systems = sorted((set(rto) | set(rpo)) & load_scoped_systems())
    out: dict[str, Target] = {}
    for system in systems:
        rto_min, tier = rto[system]
        out[system] = Target(system=system, tier=tier, rto_minutes=rto_min, rpo_minutes=rpo[system])
    return out


def backup_failures_exist(system: str) -> bool:
    for _, line, _ in scan_lines():
        m = BACKUP_RESULT_RE.match(line)
        if (
            m
            and m.group("system") == system
            and backup_row_counts(m)
            and m.group("status") in BACKUP_FAILURE_STATUSES
        ):
            return True
    return False


def backup_metric_counts(m: re.Match[str], system: str) -> bool:
    if not backup_row_counts(m) or m.group("system") != system:
        return False
    if backup_failures_exist(system):
        return m.group("status") in BACKUP_FAILURE_STATUSES
    return True


def failover_step_from_postmortem(source: str) -> bool:
    return source == POSTMORTEM_STEP_SOURCE


def observed_rto_for(system: str) -> int:
    values: list[int] = []
    for _, line, _ in scan_lines():
        m = BACKUP_RESULT_RE.match(line)
        if m and m.group("system") == system:
            if backup_metric_counts(m, system):
                values.append(int(m.group("recovery")))
            continue
        m = RECOVERY_TEST_RE.match(line)
        if m and m.group("system") == system:
            if recovery_test_row_counts(m) and m.group("status") == "failed":
                values.append(int(m.group("rto")))
            continue
        m = FAILOVER_STEP_RE.match(line)
        if m and m.group("system") == system and m.group("action") in {
            "promote_secondary",
            "flush_and_rebuild",
        }:
            if (
                within_assessment_window(m.group("ts"))
                and failover_step_from_postmortem(m.group("source"))
                and m.group("source_region") == "us-east-1"
                and m.group("target_region") == "eu-west-1"
            ):
                values.append(int(m.group("elapsed")))
            continue
        m = MONITORING_PROBE_RE.match(line)
        if m and m.group("system") == system and monitoring_probe_row_counts(m):
            values.append(int(m.group("recovery")))
    return max(values) if values else 0


def observed_rpo_for(system: str) -> int:
    values: list[int] = []
    for _, line, _ in scan_lines():
        m = BACKUP_RESULT_RE.match(line)
        if m and m.group("system") == system:
            if backup_metric_counts(m, system):
                values.append(int(m.group("loss")))
            continue
        m = RECOVERY_TEST_RE.match(line)
        if m and m.group("system") == system:
            if recovery_test_row_counts(m) and m.group("status") == "failed":
                values.append(int(m.group("rpo")))
            continue
        m = REPLICATION_LAG_RE.match(line)
        if m and m.group("system") == system:
            if replication_row_counts(m):
                values.append(math.ceil(int(m.group("lag")) / 60))
            continue
        m = RESTORE_CHECKPOINT_RE.match(line)
        if m and m.group("system") == system:
            if restore_checkpoint_row_counts(m):
                values.append(int(m.group("loss")))
    return max(values) if values else 0


def load_runbook_issues() -> list[dict]:
    issues: dict[str, dict | None] = {}
    for _, line, _ in scan_lines():
        m = RUNBOOK_STATUS_RE.match(line)
        if not m:
            continue
        system = m.group("system")
        if m.group("status") == "current":
            issues[system] = None
            continue
        issues[system] = {
            "system": system,
            "status": m.group("status"),
            "last_review": m.group("review"),
            "source_relpath": m.group("source"),
        }
    rows = [row for row in issues.values() if row is not None and row["system"] in load_scoped_systems()]
    rows.sort(key=lambda x: x["system"])
    return rows


def load_failover_blockers() -> list[dict]:
    blockers_map: dict[tuple[str, str, str], dict] = {}
    for _, line, _ in scan_lines():
        m = FAILOVER_DEP_RE.match(line)
        if m:
            key = (m.group("system"), m.group("depends"), m.group("gate"))
            kind = "FAILOVER_DEP"
            entry = {
                "system": m.group("system"),
                "depends_on": m.group("depends"),
                "blocker_gate": m.group("gate"),
                "evidence_source": m.group("source"),
                "_prio": BLOCKER_SOURCE_PRIORITY[kind],
            }
            current = blockers_map.get(key)
            if current is None or entry["_prio"] > current["_prio"]:
                blockers_map[key] = entry
            elif entry["_prio"] == current["_prio"] and current is not None:
                pass
            continue
        m = FAILOVER_STEP_BLOCKED_RE.match(line)
        if m and failover_step_from_postmortem(m.group("source")):
            key = (m.group("system"), m.group("depends"), m.group("gate"))
            kind = "FAILOVER_STEP_BLOCKED"
            entry = {
                "system": m.group("system"),
                "depends_on": m.group("depends"),
                "blocker_gate": m.group("gate"),
                "evidence_source": m.group("source"),
                "_prio": BLOCKER_SOURCE_PRIORITY[kind],
            }
            current = blockers_map.get(key)
            if current is None or entry["_prio"] > current["_prio"]:
                blockers_map[key] = entry
    scoped = load_scoped_systems()
    blockers = [
        {k: v for k, v in row.items() if k != "_prio"}
        for row in blockers_map.values()
        if row["system"] in scoped
    ]
    blockers.sort(key=lambda x: (x["system"], x["depends_on"]))
    return blockers


def load_failover_steps() -> list[dict]:
    steps: list[dict] = []
    for _, line, _ in scan_lines():
        m = FAILOVER_STEP_RE.match(line)
        if m and failover_step_from_postmortem(m.group("source")):
            steps.append(
                {
                    "ts_utc": m.group("ts"),
                    "system": m.group("system"),
                    "action": m.group("action"),
                    "source_region": m.group("source_region"),
                    "target_region": m.group("target_region"),
                    "elapsed_minutes": int(m.group("elapsed")),
                    "source_relpath": m.group("source"),
                }
            )
            continue
        m = FAILOVER_STEP_BLOCKED_RE.match(line)
        if m and failover_step_from_postmortem(m.group("source")):
            steps.append(
                {
                    "ts_utc": m.group("ts"),
                    "system": m.group("system"),
                    "action": "blocked",
                    "source_region": m.group("depends"),
                    "target_region": m.group("gate"),
                    "elapsed_minutes": 0,
                    "source_relpath": m.group("source"),
                }
            )
    steps.sort(key=lambda s: (s["ts_utc"], s["system"]))
    if POLICY["outputs"]["failover_timeline"].get("scoped_systems_only", False):
        scoped = load_scoped_systems()
        steps = [s for s in steps if s["system"] in scoped]
    return steps


def build_system_assessments() -> list[dict]:
    targets = load_targets()
    rows: list[dict] = []
    for system in sorted(targets):
        t = targets[system]
        obs_rto = observed_rto_for(system)
        obs_rpo = observed_rpo_for(system)
        grace = CRITICAL_RTO_GRACE if t.tier == "critical" else 0
        meets_rpo = obs_rpo == 0 if t.rpo_minutes == 0 else obs_rpo <= t.rpo_minutes
        rows.append(
            {
                "system": system,
                "tier": t.tier,
                "rto_target_minutes": t.rto_minutes,
                "rpo_target_minutes": t.rpo_minutes,
                "observed_rto_minutes": obs_rto,
                "observed_rpo_minutes": obs_rpo,
                "meets_rto": obs_rto <= t.rto_minutes + grace,
                "meets_rpo": meets_rpo,
            }
        )
    return rows


def build_gaps() -> list[dict]:
    gaps: list[dict] = []
    for row in build_system_assessments():
        if row["observed_rto_minutes"] > row["rto_target_minutes"]:
            gaps.append(
                {
                    "system": row["system"],
                    "gap_type": "rto_exceeded",
                    "target_minutes": row["rto_target_minutes"],
                    "observed_minutes": row["observed_rto_minutes"],
                    "evidence_source": _rto_evidence(row["system"]),
                }
            )
        if not row["meets_rpo"]:
            gaps.append(
                {
                    "system": row["system"],
                    "gap_type": "rpo_exceeded",
                    "target_minutes": row["rpo_target_minutes"],
                    "observed_minutes": row["observed_rpo_minutes"],
                    "evidence_source": _rpo_evidence(row["system"]),
                }
            )
    gaps.sort(key=lambda g: (g["system"], g["gap_type"]))
    return gaps


def _better_evidence(
    candidate: tuple[str, int, int],
    best: tuple[str, int, int],
) -> tuple[str, int, int]:
    c_source, c_val, c_prio = candidate
    b_source, b_val, b_prio = best
    if c_val > b_val:
        return candidate
    if c_val < b_val:
        return best
    if c_prio > b_prio:
        return candidate
    return best


def _rto_evidence(system: str) -> str:
    best = ("", -1, -1)
    for _, line, _ in scan_lines():
        m = BACKUP_RESULT_RE.match(line)
        if m and m.group("system") == system:
            if backup_metric_counts(m, system):
                val = int(m.group("recovery"))
                best = _better_evidence((m.group("source"), val, EVIDENCE_PRIORITY["BACKUP_RESULT"]), best)
            continue
        m = RECOVERY_TEST_RE.match(line)
        if m and m.group("system") == system:
            if recovery_test_row_counts(m) and m.group("status") == "failed":
                val = int(m.group("rto"))
                best = _better_evidence((m.group("source"), val, EVIDENCE_PRIORITY["RECOVERY_TEST"]), best)
            continue
        m = FAILOVER_STEP_RE.match(line)
        if m and m.group("system") == system:
            if m.group("action") in {"promote_secondary", "flush_and_rebuild"}:
                if (
                    within_assessment_window(m.group("ts"))
                    and failover_step_from_postmortem(m.group("source"))
                    and m.group("source_region") == "us-east-1"
                    and m.group("target_region") == "eu-west-1"
                ):
                    val = int(m.group("elapsed"))
                    best = _better_evidence(
                        (m.group("source"), val, EVIDENCE_PRIORITY["FAILOVER_STEP"]),
                        best,
                    )
            continue
        m = MONITORING_PROBE_RE.match(line)
        if m and m.group("system") == system and monitoring_probe_row_counts(m):
            val = int(m.group("recovery"))
            best = _better_evidence((m.group("source"), val, EVIDENCE_PRIORITY["MONITORING_PROBE"]), best)
    return best[0] if best[1] >= 0 else ""


def _rpo_evidence(system: str) -> str:
    best = ("", -1, -1)
    for _, line, _ in scan_lines():
        m = BACKUP_RESULT_RE.match(line)
        if m and m.group("system") == system:
            if backup_metric_counts(m, system):
                val = int(m.group("loss"))
                best = _better_evidence((m.group("source"), val, EVIDENCE_PRIORITY["BACKUP_RESULT"]), best)
            continue
        m = RECOVERY_TEST_RE.match(line)
        if m and m.group("system") == system:
            if recovery_test_row_counts(m) and m.group("status") == "failed":
                val = int(m.group("rpo"))
                best = _better_evidence((m.group("source"), val, EVIDENCE_PRIORITY["RECOVERY_TEST"]), best)
            continue
        m = RESTORE_CHECKPOINT_RE.match(line)
        if m and m.group("system") == system:
            if restore_checkpoint_row_counts(m):
                val = int(m.group("loss"))
                best = _better_evidence(
                    (m.group("source"), val, EVIDENCE_PRIORITY["RESTORE_CHECKPOINT"]),
                    best,
                )
            continue
        m = REPLICATION_LAG_RE.match(line)
        if m and m.group("system") == system:
            if replication_row_counts(m):
                val = math.ceil(int(m.group("lag")) / 60)
                best = _better_evidence((m.group("source"), val, EVIDENCE_PRIORITY["REPLICATION_LAG"]), best)
    return best[0] if best[1] >= 0 else ""


def rto_evidence_for(system: str) -> str:
    return _rto_evidence(system)


def rpo_evidence_for(system: str) -> str:
    return _rpo_evidence(system)


def compute_readiness_score() -> int:
    assessments = build_system_assessments()
    runbooks = load_runbook_issues()
    blockers = load_failover_blockers()
    penalties = OUTPUT_SCHEMA["penalties"]
    combined = OUTPUT_SCHEMA["combined_recovery_miss"]
    score = 100
    for row in assessments:
        rto_miss = row["observed_rto_minutes"] > row["rto_target_minutes"]
        rpo_miss = not row["meets_rpo"]
        rto_key = "rto_failure_critical" if row["tier"] == "critical" else "rto_failure_standard"
        rto_pen = penalties[rto_key]
        if combined and rto_miss and rpo_miss:
            score -= max(rto_pen, penalties["rpo_failure"])
        else:
            if rto_miss:
                score -= rto_pen
            if rpo_miss:
                score -= penalties["rpo_failure"]
    score -= penalties["runbook_outdated"] * sum(1 for r in runbooks if r["status"] == "outdated")
    score -= penalties["runbook_missing"] * sum(1 for r in runbooks if r["status"] == "missing")
    score -= penalties["runbook_draft"] * sum(1 for r in runbooks if r["status"] == "draft")
    score -= penalties["runbook_superseded"] * sum(1 for r in runbooks if r["status"] == "superseded")
    score -= penalties["failover_blocker"] * len(blockers)
    return max(0, score)


def build_rto_rpo_assessment() -> dict:
    return {
        "assessment_date_utc": ASSESSMENT_DATE_UTC,
        "systems": build_system_assessments(),
        "readiness_score": compute_readiness_score(),
    }


def build_recovery_gaps() -> dict:
    return {
        "gaps": build_gaps(),
        "runbook_issues": load_runbook_issues(),
        "failover_blockers": load_failover_blockers(),
    }


def build_dr_readiness_report(assessment: dict, gaps: dict) -> str:
    score = assessment["readiness_score"]
    rto_gap_systems = {
        g["system"] for g in gaps["gaps"] if g["gap_type"] == "rto_exceeded"
    }
    rpo_gap_systems = {
        g["system"] for g in gaps["gaps"] if g["gap_type"] == "rpo_exceeded"
    }
    rto_failures = [a for a in assessment["systems"] if a["system"] in rto_gap_systems]
    rpo_failures = [a for a in assessment["systems"] if a["system"] in rpo_gap_systems]
    rto_failures.sort(key=lambda x: x["system"])
    rpo_failures.sort(key=lambda x: x["system"])
    lines = [
        f"# {OUTPUT_SCHEMA['report_title']}",
        "",
        "## Executive Summary",
        f"HorizonPay regional failover readiness score is **{score}** as of "
        f"{assessment['assessment_date_utc']}. Evidence spans backup logs, replication "
        "reports, recovery drills, runbooks, and the March 2026 regional outage postmortem.",
        "",
        "## RTO Failures",
    ]
    if rto_failures:
        for row in rto_failures:
            evidence = next(
                g["evidence_source"]
                for g in gaps["gaps"]
                if g["system"] == row["system"] and g["gap_type"] == "rto_exceeded"
            )
            lines.append(
                f"- **{row['system']}**: observed {row['observed_rto_minutes']} min vs "
                f"target {row['rto_target_minutes']} min — `{evidence}`"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## RPO Risks"])
    if rpo_failures:
        for row in rpo_failures:
            evidence = next(
                g["evidence_source"]
                for g in gaps["gaps"]
                if g["system"] == row["system"] and g["gap_type"] == "rpo_exceeded"
            )
            lines.append(
                f"- **{row['system']}**: observed {row['observed_rpo_minutes']} min vs "
                f"target {row['rpo_target_minutes']} min — `{evidence}`"
            )
    else:
        lines.append("- None")
    lines.extend(["", "## Runbook Gaps"])
    for issue in gaps["runbook_issues"]:
        lines.append(
            f"- **{issue['system']}**: status `{issue['status']}` "
            f"(last review {issue['last_review']}) — `{issue['source_relpath']}`"
        )
    lines.extend(["", "## Failover Blockers"])
    for blocker in gaps["failover_blockers"]:
        lines.append(
            f"- **{blocker['system']}** blocked by `{blocker['depends_on']}` "
            f"gate `{blocker['blocker_gate']}` — `{blocker['evidence_source']}`"
        )
    lines.extend(["", "## Readiness Score", "", f"Overall readiness score: **{score}**.", ""])
    return "\n".join(lines)


def build_failover_timeline() -> str:
    steps = load_failover_steps()
    lines = [
        f"# {OUTPUT_SCHEMA['timeline_title']}",
        "",
        "| ts_utc | system | action | source_region | target_region | elapsed_minutes | source_relpath |",
        OUTPUT_SCHEMA["timeline_separator"],
    ]
    for step in steps:
        lines.append(
            f"| {step['ts_utc']} | {step['system']} | {step['action']} | "
            f"{step['source_region']} | {step['target_region']} | "
            f"{step['elapsed_minutes']} | {step['source_relpath']} |"
        )
    lines.append("")
    return "\n".join(lines)


def compute_expected() -> tuple[dict, dict, str, str]:
    assessment = build_rto_rpo_assessment()
    gaps = build_recovery_gaps()
    report = build_dr_readiness_report(assessment, gaps)
    timeline = build_failover_timeline()
    return assessment, gaps, report, timeline
