from __future__ import annotations

import argparse
import csv
import hashlib
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


def _empty_actions() -> dict:
    return {
        "actions": [],
        "alerts": [],
        "meta": {
            "source_count": 0,
            "action_counts": {"call_now": 0, "send_sms": 0, "standard_return": 0},
            "severity_counts": {"critical": 0, "warning": 0, "info": 0},
            "owner_counts": {},
        },
    }


def _channel_for(action: str, owner: str, rules: dict) -> str:
    overrides = rules.get("owner_channel_overrides") if isinstance(rules.get("owner_channel_overrides"), dict) else {}
    owner_rules = overrides.get(owner) if isinstance(overrides, dict) else None
    if isinstance(owner_rules, dict) and action in owner_rules:
        return str(owner_rules[action])
    channels = rules.get("action_channels") if isinstance(rules.get("action_channels"), dict) else {}
    return str(channels.get(action, "portal"))


def build_actions(plan_path: str, rules_path: str) -> dict:
    try:
        plan = _read_json(plan_path)
    except Exception:
        return _empty_actions()
    scheduled = plan.get("scheduled") if isinstance(plan, dict) else None
    overflow = plan.get("overflow") if isinstance(plan, dict) else None
    if not isinstance(scheduled, list) or not isinstance(overflow, list):
        return _empty_actions()
    try:
        rules = _read_json(rules_path)
    except Exception:
        rules = {}
    alert_reasons_raw = rules.get("alert_reasons")
    alert_reasons = set(_list_value(alert_reasons_raw)) if isinstance(alert_reasons_raw, list) else {"capacity_exceeded", "unknown_site"}
    reason_action_overrides = _nested_string_mapping(rules.get("reason_action_overrides"))
    actions: list[dict] = []
    for item in scheduled:
        if not isinstance(item, dict):
            continue
        request_id = str(item.get("request_id", "unknown_request") or "unknown_request")
        owner = str(item.get("owner", "unassigned") or "unassigned")
        priority = str(item.get("priority", ""))
        risk_tier = str(item.get("risk_tier", "routine") or "routine")
        if risk_tier == "urgent":
            action = "call_now"
            severity = "critical"
            reason_codes = ["risk_urgent"]
        elif priority == "P1":
            action = "call_now"
            severity = "warning"
            reason_codes = ["priority_P1"]
        else:
            action = "standard_return"
            severity = "info"
            reason_codes = ["standard_return"]
        actions.append({"request_id": request_id, "channel": _channel_for(action, owner, rules), "action": action, "severity": severity, "owner": owner, "reason_codes": reason_codes})
    for item in overflow:
        if not isinstance(item, dict):
            continue
        request_id = str(item.get("request_id", "unknown_request") or "unknown_request")
        owner = str(item.get("owner", "unassigned") or "unassigned")
        reason = str(item.get("reason", "standard_return") or "standard_return")
        hold_codes = _safe_hold_codes(item.get("hold_codes"))
        if reason in {"capacity_exceeded", "owner_capacity_exceeded", "manual_hold"}:
            action = "call_now"
            severity = "critical"
        elif reason in {"unknown_site", "site_service_blocked"}:
            action = "send_sms"
            severity = "warning"
        else:
            action = "standard_return"
            severity = "info"
        override = reason_action_overrides.get(reason, {})
        override_action = override.get("action")
        override_severity = override.get("severity")
        if override_action in VALID_ACTIONS:
            action = override_action
        if override_severity in SEVERITY_ORDER:
            severity = override_severity
        reason_codes = [reason]
        if reason == "manual_hold":
            reason_codes.extend(hold_codes)
        actions.append({"request_id": request_id, "channel": _channel_for(action, owner, rules), "action": action, "severity": severity, "owner": owner, "reason_codes": reason_codes})
    actions.sort(key=lambda row: (SEVERITY_ORDER[row["severity"]], row["owner"], row["request_id"]))
    action_counts = {"call_now": 0, "send_sms": 0, "standard_return": 0}
    severity_counts = {"critical": 0, "warning": 0, "info": 0}
    owner_counts: dict[str, int] = {}
    alert_groups: dict[tuple[str, str, str], list[str]] = {}
    for row in actions:
        action_counts[row["action"]] += 1
        severity_counts[row["severity"]] += 1
        owner_counts[row["owner"]] = owner_counts.get(row["owner"], 0) + 1
        reason = row["reason_codes"][0]
        if reason in alert_reasons:
            alert_groups.setdefault((row["severity"], row["owner"], reason), []).append(row["request_id"])
    alert_items = sorted(alert_groups.items(), key=lambda item: (SEVERITY_ORDER[item[0][0]], item[0][1], item[0][2]))
    alerts = []
    for idx, ((severity, owner, reason), request_ids) in enumerate(alert_items, start=1):
        alerts.append({"alert_id": f"A-{idx:03d}", "severity": severity, "owner": owner, "reason": reason, "request_ids": sorted(request_ids)})
    return {
        "actions": actions,
        "alerts": alerts,
        "meta": {
            "source_count": len(scheduled) + len(overflow),
            "action_counts": action_counts,
            "severity_counts": severity_counts,
            "owner_counts": dict(sorted(owner_counts.items())),
        },
    }


def actions_command(args: argparse.Namespace) -> int:
    _write_json(args.output, build_actions(args.plan, args.rules))
    return 0


def _empty_audit() -> dict:
    digest = hashlib.sha256(b"").hexdigest()[:16]
    return {
        "review_items": [],
        "owner_summary": {},
        "meta": {
            "source_count": 0,
            "assigned_count": 0,
            "deferred_count": 0,
            "invalid_count": 0,
            "severity_counts": {"critical": 0, "warning": 0, "info": 0},
            "digest": digest,
        },
    }


def _safe_list_of_dicts(data: dict, key: str) -> list[dict] | None:
    value = data.get(key) if isinstance(data, dict) else None
    if not isinstance(value, list):
        return None
    return [item for item in value if isinstance(item, dict)]


def _safe_reason_codes(raw: object) -> list[str]:
    values = _list_value(raw)
    if values:
        return values
    return ["standard_return"]


def _policy_int_map(policy: dict, key: str) -> dict[str, int]:
    return _int_mapping(policy.get(key))


def _policy_list_map(policy: dict, key: str) -> dict[str, set[str]]:
    return _list_set_map(policy.get(key))


def _expected_from_plan(plan_row: dict, source: str, rules: dict) -> dict:
    owner = str(plan_row.get("owner", "unassigned") or "unassigned")
    request_id = str(plan_row.get("request_id", "unknown_request") or "unknown_request")
    if source == "scheduled":
        priority = str(plan_row.get("priority", ""))
        risk_tier = str(plan_row.get("risk_tier", "routine") or "routine")
        if risk_tier == "urgent":
            action = "call_now"
            severity = "critical"
            reason_codes = ["risk_urgent"]
        elif priority == "P1":
            action = "call_now"
            severity = "warning"
            reason_codes = ["priority_P1"]
        else:
            action = "standard_return"
            severity = "info"
            reason_codes = ["standard_return"]
    else:
        reason = str(plan_row.get("reason", "standard_return") or "standard_return")
        hold_codes = _safe_hold_codes(plan_row.get("hold_codes"))
        if reason in {"capacity_exceeded", "owner_capacity_exceeded", "manual_hold"}:
            action = "call_now"
            severity = "critical"
        elif reason in {"unknown_site", "site_service_blocked"}:
            action = "send_sms"
            severity = "warning"
        else:
            action = "standard_return"
            severity = "info"
        overrides = _nested_string_mapping(rules.get("reason_action_overrides"))
        override = overrides.get(reason, {})
        if override.get("action") in VALID_ACTIONS:
            action = override["action"]
        if override.get("severity") in SEVERITY_ORDER:
            severity = override["severity"]
        reason_codes = [reason]
        if reason == "manual_hold":
            reason_codes.extend(hold_codes)
    return {
        "request_id": request_id,
        "owner": owner,
        "action": action,
        "severity": severity,
        "channel": _channel_for(action, owner, rules),
        "reason_codes": reason_codes,
    }


def build_audit(clean_path: str, plan_path: str, actions_path: str, rules_path: str, policy_path: str) -> dict:
    try:
        clean = _read_json(clean_path)
        plan = _read_json(plan_path)
        action_packet = _read_json(actions_path)
    except Exception:
        return _empty_audit()
    accepted = _safe_list_of_dicts(clean, "accepted")
    scheduled = _safe_list_of_dicts(plan, "scheduled")
    overflow = _safe_list_of_dicts(plan, "overflow")
    actions = _safe_list_of_dicts(action_packet, "actions")
    if accepted is None or scheduled is None or overflow is None or actions is None:
        return _empty_audit()
    try:
        rules = _read_json(rules_path)
    except Exception:
        rules = {}
    try:
        policy = _read_json(policy_path)
    except Exception:
        policy = {}
    action_minutes = _policy_int_map(policy, "review_minutes_by_action")
    severity_multiplier = _policy_int_map(policy, "severity_multiplier")
    reason_minutes = _policy_int_map(policy, "reason_minutes")
    hold_code_minutes = 0
    try:
        hold_code_minutes = int(policy.get("hold_code_minutes", 0)) if isinstance(policy, dict) else 0
    except Exception:
        hold_code_minutes = 0
    owner_caps = _policy_int_map(policy, "owner_review_cap")
    owner_blocked = _policy_list_map(policy, "owner_blocked_reasons")
    prefix = str(policy.get("batch_prefix", "CF") if isinstance(policy, dict) else "CF")
    clean_ids = {str(row.get("request_id", "")) for row in accepted if isinstance(row, dict)}
    plan_index: dict[str, tuple[str, dict]] = {}
    for row in scheduled:
        rid = str(row.get("request_id", "unknown_request") or "unknown_request")
        plan_index.setdefault(rid, ("scheduled", row))
    for row in overflow:
        rid = str(row.get("request_id", "unknown_request") or "unknown_request")
        plan_index.setdefault(rid, ("overflow", row))
    normalized_actions: list[dict] = []
    for item in actions:
        reason_codes = _safe_reason_codes(item.get("reason_codes"))
        normalized_actions.append({
            "request_id": str(item.get("request_id", "unknown_request") or "unknown_request"),
            "owner": str(item.get("owner", "unassigned") or "unassigned"),
            "action": str(item.get("action", "standard_return") or "standard_return"),
            "severity": str(item.get("severity", "info") or "info"),
            "channel": str(item.get("channel", "portal") or "portal"),
            "reason_codes": reason_codes,
        })
    normalized_actions.sort(key=lambda row: (SEVERITY_ORDER.get(row["severity"], 99), row["owner"], row["request_id"]))
    owner_minutes = {owner: 0 for owner in owner_caps}
    owners_seen = set(owner_caps)
    review_items: list[dict] = []
    for row in normalized_actions:
        request_id = row["request_id"]
        owner = row["owner"]
        owners_seen.add(owner)
        source = "missing_plan"
        codes: list[str] = []
        expected: dict | None = None
        if request_id not in plan_index:
            codes.append("request_not_in_plan")
        else:
            source, plan_row = plan_index[request_id]
            expected = _expected_from_plan(plan_row, source, rules)
            if request_id not in clean_ids:
                codes.append("request_not_in_clean")
            if owner != expected["owner"]:
                codes.append("owner_mismatch")
            if row["action"] != expected["action"]:
                codes.append("action_mismatch")
            if row["severity"] != expected["severity"]:
                codes.append("severity_mismatch")
            if row["channel"] != expected["channel"]:
                codes.append("channel_mismatch")
            if row["reason_codes"] != expected["reason_codes"]:
                codes.append("reason_code_mismatch")
        first_reason = row["reason_codes"][0] if row["reason_codes"] else "standard_return"
        if codes:
            review_minutes = 0
            status = "invalid"
            batch_key = "-"
        else:
            multiplier = severity_multiplier.get(row["severity"], 1)
            review_minutes = action_minutes.get(row["action"], 0) * multiplier + reason_minutes.get(first_reason, 0) + hold_code_minutes * max(0, len(row["reason_codes"]) - 1)
            if first_reason in owner_blocked.get(owner, set()):
                status = "deferred"
                codes = ["owner_reason_blocked"]
                batch_key = "-"
            elif owner in owner_caps and owner_minutes.get(owner, 0) + review_minutes > owner_caps[owner]:
                status = "deferred"
                codes = ["review_cap_exceeded"]
                batch_key = "-"
            else:
                status = "assigned"
                batch_key = f"{prefix}-{owner.replace(' ', '_')}-{row['severity']}-{first_reason}"
                owner_minutes[owner] = owner_minutes.get(owner, 0) + review_minutes
        review_items.append({
            "request_id": request_id,
            "owner": owner,
            "source": source,
            "action": row["action"],
            "severity": row["severity"],
            "first_reason": first_reason,
            "review_minutes": review_minutes,
            "review_status": status,
            "review_codes": codes,
            "batch_key": batch_key,
        })
    summary: dict[str, dict] = {}
    for owner in sorted(owners_seen):
        cap = owner_caps[owner] if owner in owner_caps else None
        summary[owner] = {"cap": cap, "minutes_used": owner_minutes.get(owner, 0), "assigned_count": 0, "deferred_count": 0, "invalid_count": 0}
    severity_counts = {"critical": 0, "warning": 0, "info": 0}
    for item in review_items:
        if item["severity"] in severity_counts:
            severity_counts[item["severity"]] += 1
        owner_stats = summary.setdefault(item["owner"], {"cap": owner_caps.get(item["owner"]), "minutes_used": owner_minutes.get(item["owner"], 0), "assigned_count": 0, "deferred_count": 0, "invalid_count": 0})
        owner_stats[f"{item['review_status']}_count"] += 1
    lines = []
    for item in review_items:
        codes_csv = ",".join(item["review_codes"])
        lines.append("|".join([str(item["request_id"]), str(item["owner"]), str(item["source"]), str(item["action"]), str(item["severity"]), str(item["first_reason"]), str(item["review_minutes"]), str(item["review_status"]), codes_csv, str(item["batch_key"])]))
    digest = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]
    return {
        "review_items": review_items,
        "owner_summary": dict(sorted(summary.items())),
        "meta": {
            "source_count": len(review_items),
            "assigned_count": sum(1 for item in review_items if item["review_status"] == "assigned"),
            "deferred_count": sum(1 for item in review_items if item["review_status"] == "deferred"),
            "invalid_count": sum(1 for item in review_items if item["review_status"] == "invalid"),
            "severity_counts": severity_counts,
            "digest": digest,
        },
    }


def audit_command(args: argparse.Namespace) -> int:
    _write_json(args.output, build_audit(args.clean, args.plan, args.actions, args.rules, args.policy))
    return 0


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
    audit = sub.add_parser("audit")
    audit.add_argument("--clean", default="/app/output/m1_clean.json")
    audit.add_argument("--plan", default="/app/output/m2_plan.json")
    audit.add_argument("--actions", default="/app/output/m3_actions.json")
    audit.add_argument("--rules", default="/app/data/service_rules.json")
    audit.add_argument("--policy", default="/app/data/review_policy.json")
    audit.add_argument("--output", default="/app/output/m4_audit.json")
    audit.set_defaults(func=audit_command)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except NotImplementedError as exc:
        print(str(exc))
        return 2
