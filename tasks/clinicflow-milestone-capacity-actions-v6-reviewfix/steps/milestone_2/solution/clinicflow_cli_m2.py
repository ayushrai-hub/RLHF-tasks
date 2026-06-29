from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FIELDNAMES = [
    "request_id",
    "patient_id",
    "service",
    "priority",
    "age",
    "arrival_min",
    "needs_transport",
    "site",
]
ISSUE_ORDER = [
    "malformed",
    "blank",
    "non_numeric",
    "negative",
    "unknown_service",
    "disabled_service",
    "duplicate_request",
    "invalid_priority",
]
PRIORITY_ORDER = {"P1": 0, "P2": 1, "P3": 2}
OVERFLOW_ORDER = {
    "manual_hold": 0,
    "owner_capacity_exceeded": 1,
    "capacity_exceeded": 2,
    "site_service_blocked": 3,
    "unknown_site": 4,
    "unknown_service": 5,
}
SEVERITY_ORDER = {"critical": 0, "warning": 1, "info": 2}
VALID_ACTIONS = {"call_now", "send_sms", "standard_return"}


def _read_json(path: str) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, dict):
        return data
    return {}


def _write_json(path: str, data: dict) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _bool_value(raw: str) -> bool | None:
    value = raw.strip().lower()
    if value == "true":
        return True
    if value == "false":
        return False
    return None


def _int_value(raw: str) -> int | None:
    try:
        return int(raw.strip())
    except Exception:
        return None


def _ordered_issues(issues: list[str]) -> list[str]:
    return [issue for issue in ISSUE_ORDER if issue in issues]


def _string_map(raw: object) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    return {str(key): str(value) for key, value in raw.items()}


def _int_mapping(raw: object) -> dict[str, int]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, int] = {}
    for key, value in raw.items():
        try:
            result[str(key)] = int(value)
        except Exception:
            result[str(key)] = 0
    return result


def _nested_int_mapping(raw: object) -> dict[str, dict[str, int]]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, int]] = {}
    for outer, inner in raw.items():
        if isinstance(inner, dict):
            result[str(outer)] = _int_mapping(inner)
    return result


def _nested_string_mapping(raw: object) -> dict[str, dict[str, str]]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for outer, inner in raw.items():
        if isinstance(inner, dict):
            result[str(outer)] = _string_map(inner)
    return result


def _list_set_map(raw: object) -> dict[str, set[str]]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, set[str]] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            result[str(key)] = {str(item) for item in value}
    return result


def _list_map(raw: object) -> dict[str, list[str]]:
    if not isinstance(raw, dict):
        return {}
    result: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            result[str(key)] = [str(item) for item in value]
    return result


def _list_value(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _risk_thresholds(rules: dict) -> tuple[int, int]:
    urgent = 45
    watch = 30
    raw = rules.get("risk_tier_thresholds")
    if isinstance(raw, dict):
        try:
            urgent = int(raw.get("urgent", urgent))
        except Exception:
            urgent = 45
        try:
            watch = int(raw.get("watch", watch))
        except Exception:
            watch = 30
    return urgent, watch


def _risk_tier(score: int, rules: dict) -> str:
    urgent, watch = _risk_thresholds(rules)
    if score >= urgent:
        return "urgent"
    if score >= watch:
        return "watch"
    return "routine"


def _hold_codes(patient_id: str, patient_flags: dict[str, list[str]], hold_flags: set[str]) -> list[str]:
    return _dedupe([flag for flag in patient_flags.get(patient_id, []) if flag in hold_flags])


def _row_is_malformed(row: dict | None) -> bool:
    if row is None or None in row:
        return True
    return any(row.get(field) is None for field in FIELDNAMES)


def normalize_rows(input_path: str, rules_path: str) -> dict:
    try:
        rules = _read_json(rules_path)
    except Exception:
        rules = {}
    weights = _int_mapping(rules.get("service_weights"))
    bonus = _int_mapping(rules.get("priority_bonus"))
    disabled = set(_list_value(rules.get("disabled_services")))
    service_aliases = _string_map(rules.get("service_aliases"))
    site_aliases = _string_map(rules.get("site_aliases"))
    priority_aliases = _string_map(rules.get("priority_aliases"))
    site_score_bonus = _int_mapping(rules.get("site_score_bonus"))
    patient_flags = _list_map(rules.get("patient_flags"))
    flag_score_bonus = _int_mapping(rules.get("flag_score_bonus"))
    hold_flags = set(_list_value(rules.get("hold_flags")))
    accepted: list[dict] = []
    rejects: list[dict] = []
    seen_request_ids: set[str] = set()
    source_count = 0
    try:
        with Path(input_path).open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for idx, row in enumerate(reader, start=2):
                source_count += 1
                request_id = ""
                if isinstance(row, dict):
                    request_id = str(row.get("request_id") or "").strip()
                if _row_is_malformed(row):
                    rejects.append({"request_id": request_id, "line": idx, "issues": ["malformed"]})
                    continue
                assert row is not None
                patient_id = str(row.get("patient_id") or "").strip()
                raw_service = str(row.get("service") or "").strip()
                service = service_aliases.get(raw_service, raw_service)
                raw_priority = str(row.get("priority") or "").strip()
                priority = priority_aliases.get(raw_priority, raw_priority)
                raw_site = str(row.get("site") or "").strip()
                site = site_aliases.get(raw_site, raw_site)
                issues: list[str] = []
                if not request_id or not patient_id:
                    issues.append("blank")
                age = _int_value(str(row.get("age") or ""))
                arrival = _int_value(str(row.get("arrival_min") or ""))
                transport = _bool_value(str(row.get("needs_transport") or ""))
                if age is None or arrival is None or transport is None:
                    issues.append("non_numeric")
                if arrival is not None and arrival < 0:
                    issues.append("negative")
                if service not in weights:
                    issues.append("unknown_service")
                elif service in disabled:
                    issues.append("disabled_service")
                if priority not in PRIORITY_ORDER:
                    issues.append("invalid_priority")
                if not issues and request_id in seen_request_ids:
                    issues.append("duplicate_request")
                if issues:
                    rejects.append({"request_id": request_id, "line": idx, "issues": _ordered_issues(issues)})
                    continue
                seen_request_ids.add(request_id)
                score = int(weights[service]) + int(bonus.get(priority, 0))
                if age is not None and age >= 65:
                    score += 5
                if transport is True:
                    score += 3
                score += int(site_score_bonus.get(site, 0))
                for flag in patient_flags.get(patient_id, []):
                    score += int(flag_score_bonus.get(flag, 0))
                tier = _risk_tier(score, rules)
                holds = _hold_codes(patient_id, patient_flags, hold_flags)
                accepted.append({
                    "request_id": request_id,
                    "patient_id": patient_id,
                    "service": service,
                    "priority": priority,
                    "site": site,
                    "arrival_min": arrival,
                    "needs_transport": transport,
                    "triage_score": score,
                    "risk_tier": tier,
                    "hold_codes": holds,
                })
    except FileNotFoundError:
        source_count = 0
    accepted.sort(key=lambda row: (PRIORITY_ORDER[row["priority"]], -row["triage_score"], row["arrival_min"], row["request_id"]))
    rejects.sort(key=lambda row: (row["line"], row["request_id"]))
    priority_counts = {"P1": 0, "P2": 0, "P3": 0}
    service_counts: dict[str, int] = {}
    risk_tier_counts = {"urgent": 0, "watch": 0, "routine": 0}
    hold_count = 0
    for row in accepted:
        priority_counts[row["priority"]] += 1
        service_counts[row["service"]] = service_counts.get(row["service"], 0) + 1
        risk_tier_counts[row["risk_tier"]] += 1
        if row["hold_codes"]:
            hold_count += 1
    return {
        "accepted": accepted,
        "rejects": rejects,
        "meta": {
            "source_count": source_count,
            "accepted_count": len(accepted),
            "rejected_count": len(rejects),
            "priority_counts": priority_counts,
            "service_counts": dict(sorted(service_counts.items())),
            "risk_tier_counts": risk_tier_counts,
            "hold_count": hold_count,
        },
    }


def normalize_command(args: argparse.Namespace) -> int:
    _write_json(args.output, normalize_rows(args.input, args.rules))
    return 0


def _empty_plan() -> dict:
    return {
        "scheduled": [],
        "overflow": [],
        "meta": {
            "source_count": 0,
            "scheduled_count": 0,
            "overflow_count": 0,
            "owner_counts": {},
            "capacity_used": {},
            "owner_capacity_used": {},
        },
    }


def _safe_hold_codes(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return _dedupe([str(item) for item in raw])


def build_plan(clean_path: str, rules_path: str) -> dict:
    try:
        clean = _read_json(clean_path)
    except Exception:
        return _empty_plan()
    accepted = clean.get("accepted") if isinstance(clean, dict) else None
    if not isinstance(accepted, list):
        return _empty_plan()
    try:
        rules = _read_json(rules_path)
    except Exception:
        rules = {}
    durations = _int_mapping(rules.get("durations"))
    buffers = _int_mapping(rules.get("service_buffer_min"))
    risk_buffers = _int_mapping(rules.get("risk_tier_buffer_min"))
    site_duration_overrides = _nested_int_mapping(rules.get("site_service_duration_overrides"))
    capacities = _int_mapping(rules.get("site_capacity"))
    start_offsets = _int_mapping(rules.get("site_start_min"))
    reserves = _int_mapping(rules.get("priority_capacity_reserve"))
    owner_caps = _int_mapping(rules.get("owner_capacity_cap"))
    owners = _string_map(rules.get("site_owner"))
    blocks = _list_set_map(rules.get("site_service_blocks"))
    used = {site: 0 for site in capacities}
    used["unknown"] = 0
    owner_used: dict[str, int] = {owner: 0 for owner in owner_caps}
    owner_counts: dict[str, int] = {}
    scheduled: list[dict] = []
    overflow: list[dict] = []
    for item in accepted:
        if not isinstance(item, dict):
            continue
        request_id = str(item.get("request_id", ""))
        service = str(item.get("service", ""))
        priority = str(item.get("priority", ""))
        raw_site = str(item.get("site", ""))
        risk_tier = str(item.get("risk_tier", "routine") or "routine")
        if risk_tier not in {"urgent", "watch", "routine"}:
            risk_tier = "routine"
        hold_codes = _safe_hold_codes(item.get("hold_codes"))
        known_site = raw_site in capacities and raw_site in owners
        site_id = raw_site if known_site else "unknown"
        owner = owners.get(site_id, "unassigned") if known_site else "unassigned"
        owner_counts[owner] = owner_counts.get(owner, 0) + 1
        known_service = service in durations
        if known_service:
            base_duration = site_duration_overrides.get(site_id, {}).get(service, int(durations.get(service, 0)))
            charged_minutes = int(base_duration) + int(buffers.get(service, 0)) + int(risk_buffers.get(risk_tier, 0))
        else:
            charged_minutes = 0
        overflow_base = {
            "request_id": request_id,
            "site_id": site_id,
            "owner": owner,
            "priority": priority,
            "duration": charged_minutes,
            "risk_tier": risk_tier,
            "hold_codes": hold_codes,
        }
        if not known_site:
            overflow.append({**overflow_base, "site_id": "unknown", "owner": "unassigned", "reason": "unknown_site"})
            continue
        if not known_service:
            overflow.append({**overflow_base, "reason": "unknown_service", "duration": 0})
            continue
        if hold_codes:
            overflow.append({**overflow_base, "reason": "manual_hold"})
            continue
        if service in blocks.get(site_id, set()):
            overflow.append({**overflow_base, "reason": "site_service_blocked"})
            continue
        capacity_limit = capacities[site_id]
        if priority != "P1":
            capacity_limit = max(0, capacity_limit - reserves.get(site_id, 0))
        if used[site_id] + charged_minutes > capacity_limit:
            overflow.append({**overflow_base, "reason": "capacity_exceeded"})
            continue
        if owner in owner_caps and owner_used.get(owner, 0) + charged_minutes > owner_caps[owner]:
            owner_used.setdefault(owner, owner_used.get(owner, 0))
            overflow.append({**overflow_base, "reason": "owner_capacity_exceeded"})
            continue
        start = start_offsets.get(site_id, 0) + used[site_id]
        end = start + charged_minutes
        used[site_id] += charged_minutes
        owner_used[owner] = owner_used.get(owner, 0) + charged_minutes
        scheduled.append({
            "request_id": request_id,
            "site_id": site_id,
            "owner": owner,
            "service": service,
            "priority": priority,
            "slot_start": start,
            "slot_end": end,
            "overflow": False,
            "risk_tier": risk_tier,
            "hold_codes": hold_codes,
        })
    scheduled.sort(key=lambda row: (row["site_id"], row["slot_start"], row["request_id"]))
    overflow.sort(key=lambda row: (OVERFLOW_ORDER.get(row["reason"], 99), PRIORITY_ORDER.get(row["priority"], 99), row["request_id"]))
    return {
        "scheduled": scheduled,
        "overflow": overflow,
        "meta": {
            "source_count": len(accepted),
            "scheduled_count": len(scheduled),
            "overflow_count": len(overflow),
            "owner_counts": dict(sorted(owner_counts.items())),
            "capacity_used": dict(sorted(used.items())),
            "owner_capacity_used": dict(sorted(owner_used.items())),
        },
    }


def plan_command(args: argparse.Namespace) -> int:
    _write_json(args.output, build_plan(args.clean, args.rules))
    return 0



def actions_command(args: argparse.Namespace) -> int:
    raise NotImplementedError("actions command is not implemented yet")

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clinicflow")
    sub = parser.add_subparsers(dest="command", required=True)
    normalize = sub.add_parser("normalize")
    normalize.add_argument("--input", default="/app/data/appointments.csv")
    normalize.add_argument("--rules", default="/app/data/service_rules.json")
    normalize.add_argument("--output", default="/app/output/m1_clean.json")
    normalize.set_defaults(func=normalize_command)
    plan = sub.add_parser("plan")
    plan.add_argument("--clean", default="/app/output/m1_clean.json")
    plan.add_argument("--rules", default="/app/data/service_rules.json")
    plan.add_argument("--output", default="/app/output/m2_plan.json")
    plan.set_defaults(func=plan_command)
    actions = sub.add_parser("actions")
    actions.add_argument("--plan", default="/app/output/m2_plan.json")
    actions.add_argument("--rules", default="/app/data/service_rules.json")
    actions.add_argument("--output", default="/app/output/m3_actions.json")
    actions.set_defaults(func=actions_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except NotImplementedError as exc:
        print(str(exc))
        return 2
