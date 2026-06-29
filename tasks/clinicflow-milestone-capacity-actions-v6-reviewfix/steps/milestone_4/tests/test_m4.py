from __future__ import annotations

import hashlib
import json
from pathlib import Path


def run_cli(*args: str) -> None:
    from clinicflow.cli import main

    result = main(list(args))
    assert result == 0


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def digest_for(items: list[dict]) -> str:
    lines = []
    for item in items:
        lines.append("|".join([
            str(item["request_id"]),
            str(item["owner"]),
            str(item["source"]),
            str(item["action"]),
            str(item["severity"]),
            str(item["first_reason"]),
            str(item["review_minutes"]),
            str(item["review_status"]),
            ",".join(item["review_codes"]),
            str(item["batch_key"]),
        ]))
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()[:16]


def build_all(tmp_path: Path) -> tuple[Path, Path, Path]:
    clean = tmp_path / "m1_clean.json"
    plan = tmp_path / "m2_plan.json"
    actions = tmp_path / "m3_actions.json"
    run_cli("normalize", "--output", str(clean))
    run_cli("plan", "--clean", str(clean), "--output", str(plan))
    run_cli("actions", "--plan", str(plan), "--output", str(actions))
    return clean, plan, actions


EMPTY_AUDIT = {
    "review_items": [],
    "owner_summary": {},
    "meta": {
        "source_count": 0,
        "assigned_count": 0,
        "deferred_count": 0,
        "invalid_count": 0,
        "severity_counts": {"critical": 0, "warning": 0, "info": 0},
        "digest": hashlib.sha256(b"").hexdigest()[:16],
    },
}


class TestMilestone4:
    def test_cli_integration_audit_schema_stateful_caps_and_digest(self, tmp_path: Path) -> None:
        """Full workflow audit assigns, defers, summarizes idle cap owners, and binds the digest."""
        clean, plan, actions = build_all(tmp_path)
        output = Path("/app/output/m4_audit.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("stale", encoding="utf-8")
        run_cli("audit", "--clean", str(clean), "--plan", str(plan), "--actions", str(actions))
        first = read_json(output)
        run_cli("audit", "--clean", str(clean), "--plan", str(plan), "--actions", str(actions))
        data = read_json(output)
        assert data == first
        assert set(data.keys()) == {"review_items", "owner_summary", "meta"}
        for row in data["review_items"]:
            assert set(row.keys()) == {"request_id", "owner", "source", "action", "severity", "first_reason", "review_minutes", "review_status", "review_codes", "batch_key"}
        for row in data["owner_summary"].values():
            assert set(row.keys()) == {"cap", "minutes_used", "assigned_count", "deferred_count", "invalid_count"}
        assert set(data["meta"].keys()) == {"source_count", "assigned_count", "deferred_count", "invalid_count", "severity_counts", "digest"}
        assert [row["request_id"] for row in data["review_items"]] == ["R-108", "R-100", "R-102", "R-107", "R-101", "R-103"]
        by_id = {row["request_id"]: row for row in data["review_items"]}
        assert by_id["R-108"] == {"request_id": "R-108", "owner": "North Desk", "source": "overflow", "action": "call_now", "severity": "critical", "first_reason": "capacity_exceeded", "review_minutes": 27, "review_status": "assigned", "review_codes": [], "batch_key": "CF-North_Desk-critical-capacity_exceeded"}
        assert by_id["R-100"]["review_codes"] == ["review_cap_exceeded"]
        assert by_id["R-101"]["review_status"] == "deferred"
        assert data["owner_summary"]["Idle Desk"] == {"cap": 9, "minutes_used": 0, "assigned_count": 0, "deferred_count": 0, "invalid_count": 0}
        assert data["owner_summary"]["North Desk"] == {"cap": 30, "minutes_used": 27, "assigned_count": 1, "deferred_count": 2, "invalid_count": 0}
        assert data["meta"] == {"source_count": 6, "assigned_count": 4, "deferred_count": 2, "invalid_count": 0, "severity_counts": {"critical": 1, "warning": 3, "info": 2}, "digest": digest_for(data["review_items"])}

    def test_reconciliation_mismatch_codes_make_invalid_rows_and_skip_capacity(self, tmp_path: Path) -> None:
        """Audit recomputes expected actions and records every mismatch in deterministic code order."""
        clean = tmp_path / "clean.json"
        plan = tmp_path / "plan.json"
        actions = tmp_path / "actions.json"
        policy = tmp_path / "policy.json"
        write_json(clean, {"accepted": [{"request_id": "X-1"}]})
        write_json(plan, {"scheduled": [{"request_id": "X-1", "owner": "Ops", "priority": "P1", "risk_tier": "routine"}], "overflow": []})
        write_json(actions, {"actions": [
            {"request_id": "X-1", "owner": "Wrong", "action": "send_sms", "severity": "info", "channel": "sms", "reason_codes": ["bad_reason"]},
            {"request_id": "X-missing", "owner": "Ops", "action": "call_now", "severity": "critical", "channel": "phone", "reason_codes": ["capacity_exceeded"]},
        ]})
        write_json(policy, {"owner_review_cap": {"Ops": 100, "Wrong": 100}, "review_minutes_by_action": {"call_now": 10, "send_sms": 5, "standard_return": 1}, "severity_multiplier": {"critical": 2, "warning": 1, "info": 1}})
        output = tmp_path / "audit.json"
        run_cli("audit", "--clean", str(clean), "--plan", str(plan), "--actions", str(actions), "--policy", str(policy), "--output", str(output))
        data = read_json(output)
        by_id = {row["request_id"]: row for row in data["review_items"]}
        assert by_id["X-1"]["source"] == "scheduled"
        assert by_id["X-1"]["review_status"] == "invalid"
        assert by_id["X-1"]["review_minutes"] == 0
        assert by_id["X-1"]["review_codes"] == ["owner_mismatch", "action_mismatch", "severity_mismatch", "channel_mismatch", "reason_code_mismatch"]
        assert by_id["X-missing"]["source"] == "missing_plan"
        assert by_id["X-missing"]["review_codes"] == ["request_not_in_plan"]
        assert data["owner_summary"]["Wrong"]["minutes_used"] == 0
        assert data["meta"]["invalid_count"] == 2
        assert data["meta"]["digest"] == digest_for(data["review_items"])

    def test_stateful_review_cap_uses_sorted_audit_order_not_action_file_order(self, tmp_path: Path) -> None:
        """Earlier sorted critical rows consume owner review capacity before later lower-severity rows."""
        clean = tmp_path / "clean.json"
        plan = tmp_path / "plan.json"
        actions = tmp_path / "actions.json"
        policy = tmp_path / "policy.json"
        write_json(clean, {"accepted": [{"request_id": "A-1"}, {"request_id": "A-2"}, {"request_id": "A-3"}]})
        write_json(plan, {"scheduled": [
            {"request_id": "A-3", "owner": "Ops", "priority": "P2", "risk_tier": "routine"},
        ], "overflow": [
            {"request_id": "A-2", "owner": "Ops", "priority": "P2", "reason": "capacity_exceeded"},
            {"request_id": "A-1", "owner": "Ops", "priority": "P2", "reason": "capacity_exceeded"},
        ]})
        write_json(actions, {"actions": [
            {"request_id": "A-3", "owner": "Ops", "action": "standard_return", "severity": "info", "channel": "portal", "reason_codes": ["standard_return"]},
            {"request_id": "A-2", "owner": "Ops", "action": "call_now", "severity": "critical", "channel": "phone", "reason_codes": ["capacity_exceeded"]},
            {"request_id": "A-1", "owner": "Ops", "action": "call_now", "severity": "critical", "channel": "phone", "reason_codes": ["capacity_exceeded"]},
        ]})
        write_json(policy, {"owner_review_cap": {"Ops": 28, "Idle Desk": 5}, "review_minutes_by_action": {"call_now": 12, "standard_return": 4}, "severity_multiplier": {"critical": 2, "info": 1}, "reason_minutes": {"capacity_exceeded": 3, "standard_return": 0}, "batch_prefix": "Q"})
        output = tmp_path / "audit.json"
        run_cli("audit", "--clean", str(clean), "--plan", str(plan), "--actions", str(actions), "--policy", str(policy), "--output", str(output))
        data = read_json(output)
        assert [row["request_id"] for row in data["review_items"]] == ["A-1", "A-2", "A-3"]
        by_id = {row["request_id"]: row for row in data["review_items"]}
        assert by_id["A-1"]["review_status"] == "assigned"
        assert by_id["A-1"]["batch_key"] == "Q-Ops-critical-capacity_exceeded"
        assert by_id["A-2"]["review_status"] == "deferred"
        assert by_id["A-2"]["review_codes"] == ["review_cap_exceeded"]
        assert by_id["A-3"]["review_status"] == "deferred"
        assert by_id["A-3"]["review_codes"] == ["review_cap_exceeded"]
        assert data["owner_summary"]["Idle Desk"] == {"cap": 5, "minutes_used": 0, "assigned_count": 0, "deferred_count": 0, "invalid_count": 0}
        assert data["owner_summary"]["Ops"] == {"cap": 28, "minutes_used": 27, "assigned_count": 1, "deferred_count": 2, "invalid_count": 0}

    def test_owner_reason_blocks_and_manual_hold_extra_minutes(self, tmp_path: Path) -> None:
        """Policy block rules defer matching first reasons and manual hold codes add review minutes."""
        clean = tmp_path / "clean.json"
        plan = tmp_path / "plan.json"
        actions = tmp_path / "actions.json"
        policy = tmp_path / "policy.json"
        write_json(clean, {"accepted": [{"request_id": "H-1"}, {"request_id": "H-2"}]})
        write_json(plan, {"scheduled": [], "overflow": [
            {"request_id": "H-1", "owner": "Ops", "priority": "P2", "reason": "manual_hold", "hold_codes": ["needs_consent", "transport_gap"]},
            {"request_id": "H-2", "owner": "Ops", "priority": "P2", "reason": "unknown_site"},
        ]})
        write_json(actions, {"actions": [
            {"request_id": "H-1", "owner": "Ops", "action": "call_now", "severity": "critical", "channel": "phone", "reason_codes": ["manual_hold", "needs_consent", "transport_gap"]},
            {"request_id": "H-2", "owner": "Ops", "action": "send_sms", "severity": "warning", "channel": "sms", "reason_codes": ["unknown_site"]},
        ]})
        write_json(policy, {"owner_review_cap": {"Ops": 100}, "owner_blocked_reasons": {"Ops": ["manual_hold"]}, "review_minutes_by_action": {"call_now": 10, "send_sms": 6}, "severity_multiplier": {"critical": 2, "warning": 1}, "reason_minutes": {"manual_hold": 5, "unknown_site": 2}, "hold_code_minutes": 3})
        output = tmp_path / "audit.json"
        run_cli("audit", "--clean", str(clean), "--plan", str(plan), "--actions", str(actions), "--policy", str(policy), "--output", str(output))
        data = read_json(output)
        by_id = {row["request_id"]: row for row in data["review_items"]}
        assert by_id["H-1"]["review_minutes"] == 31
        assert by_id["H-1"]["review_status"] == "deferred"
        assert by_id["H-1"]["review_codes"] == ["owner_reason_blocked"]
        assert by_id["H-2"]["review_minutes"] == 8
        assert by_id["H-2"]["review_status"] == "assigned"
        assert data["owner_summary"]["Ops"] == {"cap": 100, "minutes_used": 8, "assigned_count": 1, "deferred_count": 1, "invalid_count": 0}

    def test_missing_or_malformed_dependency_returns_empty_audit_schema(self, tmp_path: Path) -> None:
        """Audit writes the empty schema for missing JSON and non-list dependency sections."""
        output = tmp_path / "missing" / "audit.json"
        run_cli("audit", "--clean", str(tmp_path / "missing_clean.json"), "--plan", str(tmp_path / "missing_plan.json"), "--actions", str(tmp_path / "missing_actions.json"), "--output", str(output))
        assert read_json(output) == EMPTY_AUDIT
        clean = tmp_path / "clean.json"
        plan = tmp_path / "bad_plan.json"
        actions = tmp_path / "actions.json"
        write_json(clean, {"accepted": []})
        write_json(plan, {"scheduled": [], "overflow": "bad"})
        write_json(actions, {"actions": []})
        bad_output = tmp_path / "bad_audit.json"
        run_cli("audit", "--clean", str(clean), "--plan", str(plan), "--actions", str(actions), "--output", str(bad_output))
        assert read_json(bad_output) == EMPTY_AUDIT

    def test_reason_overrides_are_used_when_recomputing_expected_action(self, tmp_path: Path) -> None:
        """Audit validation honors reason_action_overrides and owner channel overrides from the rules file."""
        clean = tmp_path / "clean.json"
        plan = tmp_path / "plan.json"
        actions = tmp_path / "actions.json"
        rules_path = tmp_path / "rules.json"
        policy = tmp_path / "policy.json"
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["reason_action_overrides"] = {"unknown_service": {"action": "call_now", "severity": "critical"}}
        rules["owner_channel_overrides"] = {"Ops": {"call_now": "pager"}}
        write_json(rules_path, rules)
        write_json(clean, {"accepted": [{"request_id": "O-1"}]})
        write_json(plan, {"scheduled": [], "overflow": [{"request_id": "O-1", "owner": "Ops", "priority": "P2", "reason": "unknown_service"}]})
        write_json(actions, {"actions": [{"request_id": "O-1", "owner": "Ops", "action": "call_now", "severity": "critical", "channel": "pager", "reason_codes": ["unknown_service"]}]})
        write_json(policy, {"owner_review_cap": {"Ops": 50}, "review_minutes_by_action": {"call_now": 10}, "severity_multiplier": {"critical": 2}, "reason_minutes": {"unknown_service": 1}})
        output = tmp_path / "audit.json"
        run_cli("audit", "--clean", str(clean), "--plan", str(plan), "--actions", str(actions), "--rules", str(rules_path), "--policy", str(policy), "--output", str(output))
        data = read_json(output)
        assert data["review_items"] == [{"request_id": "O-1", "owner": "Ops", "source": "overflow", "action": "call_now", "severity": "critical", "first_reason": "unknown_service", "review_minutes": 21, "review_status": "assigned", "review_codes": [], "batch_key": "CF-Ops-critical-unknown_service"}]
        assert data["meta"]["digest"] == digest_for(data["review_items"])
