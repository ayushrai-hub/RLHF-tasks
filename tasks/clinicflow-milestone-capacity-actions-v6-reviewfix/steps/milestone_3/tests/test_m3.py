from __future__ import annotations

import json
from pathlib import Path


def run_cli(*args: str) -> None:
    from clinicflow.cli import main

    result = main(list(args))
    assert result == 0


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_plan(tmp_path: Path, rules: Path | None = None) -> Path:
    clean = tmp_path / "m1_clean.json"
    plan = tmp_path / "m2_plan.json"
    args = ["normalize", "--output", str(clean)]
    if rules is not None:
        args.extend(["--rules", str(rules)])
    run_cli(*args)
    plan_args = ["plan", "--clean", str(clean), "--output", str(plan)]
    if rules is not None:
        plan_args.extend(["--rules", str(rules)])
    run_cli(*plan_args)
    return plan


class TestMilestone3:
    def test_cli_integration_actions_schema_counts_alert_order(self, tmp_path: Path) -> None:
        """Integration path proves action schema, counts, alerts, and ordering."""
        plan = build_plan(tmp_path)
        actions = tmp_path / "deep" / "m3_actions.json"
        plan_before = plan.read_text(encoding="utf-8")
        run_cli("actions", "--plan", str(plan), "--output", str(actions))
        assert plan.read_text(encoding="utf-8") == plan_before
        data = read_json(actions)
        assert set(data.keys()) == {"actions", "alerts", "meta"}
        for row in data["actions"]:
            assert set(row.keys()) == {"request_id", "channel", "action", "severity", "owner", "reason_codes"}
        for row in data["alerts"]:
            assert set(row.keys()) == {"alert_id", "severity", "owner", "reason", "request_ids"}
        assert set(data["meta"].keys()) == {"source_count", "action_counts", "severity_counts", "owner_counts"}
        assert set(data["meta"]["action_counts"].keys()) == {"call_now", "send_sms", "standard_return"}
        assert set(data["meta"]["severity_counts"].keys()) == {"critical", "warning", "info"}
        assert [row["request_id"] for row in data["actions"]] == ["R-108", "R-100", "R-102", "R-107", "R-101", "R-103"]
        action_by_id = {row["request_id"]: row for row in data["actions"]}
        assert action_by_id["R-108"]["reason_codes"] == ["capacity_exceeded"]
        assert action_by_id["R-108"]["channel"] == "phone"
        assert action_by_id["R-100"]["reason_codes"] == ["priority_P1"]
        assert action_by_id["R-100"]["channel"] == "phone"
        assert action_by_id["R-101"]["reason_codes"] == ["standard_return"]
        assert action_by_id["R-101"]["channel"] == "portal"
        assert action_by_id["R-107"]["reason_codes"] == ["unknown_site"]
        assert action_by_id["R-107"]["channel"] == "sms"
        assert data["meta"]["source_count"] == 6
        assert data["meta"]["action_counts"] == {"call_now": 3, "send_sms": 1, "standard_return": 2}
        assert data["meta"]["severity_counts"] == {"critical": 1, "warning": 3, "info": 2}
        assert data["meta"]["owner_counts"] == {"North Desk": 3, "West Desk": 1, "South Desk": 1, "unassigned": 1}
        assert data["alerts"] == [
            {"alert_id": "A-001", "severity": "critical", "owner": "North Desk", "reason": "capacity_exceeded", "request_ids": ["R-108"]},
            {"alert_id": "A-002", "severity": "warning", "owner": "unassigned", "reason": "unknown_site", "request_ids": ["R-107"]},
        ]

    def test_modified_channel_mapping_dependency_mutation_recomputes_channel(self, tmp_path: Path) -> None:
        """Modified action channel dependency changes standard_return channel."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["action_channels"]["standard_return"] = "email"
        del rules["action_channels"]["call_now"]
        changed = tmp_path / "changed_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        plan = build_plan(tmp_path, changed)
        actions = tmp_path / "m3_actions.json"
        run_cli("actions", "--plan", str(plan), "--rules", str(changed), "--output", str(actions))
        data = read_json(actions)
        standard = next(row for row in data["actions"] if row["action"] == "standard_return")
        assert standard["channel"] == "email"
        call_now = next(row for row in data["actions"] if row["action"] == "call_now")
        assert call_now["channel"] == "portal"
        assert data["meta"]["action_counts"]["standard_return"] == 2
        assert data["meta"]["owner_counts"]["North Desk"] == 3

    def test_missing_default_edge_branch_non_list_plan_empty_schema(self, tmp_path: Path) -> None:
        """Non-list plan edge branch returns empty schema with zero counts."""
        bad_plan = tmp_path / "bad_plan.json"
        bad_plan.write_text(json.dumps({"scheduled": {}, "overflow": []}), encoding="utf-8")
        output = tmp_path / "nested" / "m3_actions.json"
        run_cli("actions", "--plan", str(bad_plan), "--output", str(output))
        data = read_json(output)
        assert data["actions"] == []
        assert data["alerts"] == []
        assert data["meta"]["source_count"] == 0
        assert data["meta"]["action_counts"] == {"call_now": 0, "send_sms": 0, "standard_return": 0}
        assert data["meta"]["severity_counts"] == {"critical": 0, "warning": 0, "info": 0}

        missing_output = tmp_path / "missing_actions.json"
        run_cli("actions", "--plan", str(tmp_path / "missing_plan.json"), "--output", str(missing_output))
        assert read_json(missing_output) == data

        malformed_plan = tmp_path / "malformed_plan.json"
        malformed_plan.write_text("not json{{", encoding="utf-8")
        malformed_output = tmp_path / "malformed_actions.json"
        run_cli("actions", "--plan", str(malformed_plan), "--output", str(malformed_output))
        assert read_json(malformed_output) == data

        bad_overflow = tmp_path / "bad_overflow_plan.json"
        bad_overflow.write_text(json.dumps({"scheduled": [], "overflow": "bad"}), encoding="utf-8")
        bad_overflow_output = tmp_path / "bad_overflow_actions.json"
        run_cli("actions", "--plan", str(bad_overflow), "--output", str(bad_overflow_output))
        assert read_json(bad_overflow_output) == data

        fallback_plan = tmp_path / "fallback_plan.json"
        fallback_plan.write_text(
            json.dumps({
                "scheduled": [{"request_id": "S-1", "priority": "P2"}],
                "overflow": [{"owner": "Night Desk", "priority": "P3"}, {"request_id": "S-2", "owner": "unassigned", "priority": "P2", "reason": "unknown_service"}],
            }),
            encoding="utf-8",
        )
        fallback_output = tmp_path / "fallback" / "m3_actions.json"
        run_cli("actions", "--plan", str(fallback_plan), "--output", str(fallback_output))
        fallback_data = read_json(fallback_output)
        by_request = {row["request_id"]: row for row in fallback_data["actions"]}
        assert by_request["S-1"]["owner"] == "unassigned"
        assert by_request["S-1"]["reason_codes"] == ["standard_return"]
        assert by_request["unknown_request"]["reason_codes"] == ["standard_return"]
        assert by_request["unknown_request"]["action"] == "standard_return"
        assert by_request["S-2"]["reason_codes"] == ["unknown_service"]
        assert fallback_data["alerts"] == []

    def test_grouped_multi_request_alerts_and_owner_counts(self, tmp_path: Path) -> None:
        """Synthetic plan proves grouped alert request ordering and owner counts."""
        plan = tmp_path / "alert_plan.json"
        plan.write_text(
            json.dumps({
                "scheduled": [
                    {"request_id": "N-2", "priority": "P1", "owner": "North Desk"},
                    {"request_id": "N-1", "priority": "P2", "owner": "North Desk"},
                ],
                "overflow": [
                    {"request_id": "C-2", "owner": "Ops", "priority": "P2", "reason": "capacity_exceeded"},
                    {"request_id": "U-2", "owner": "Zone", "priority": "P2", "reason": "unknown_site"},
                    {"request_id": "C-1", "owner": "Ops", "priority": "P3", "reason": "capacity_exceeded"},
                    {"request_id": "U-1", "owner": "Zone", "priority": "P1", "reason": "unknown_site"},
                    {"request_id": "X-1", "owner": "Zone", "priority": "P1", "reason": "unknown_service"},
                ],
            }),
            encoding="utf-8",
        )
        output = tmp_path / "grouped_actions.json"
        run_cli("actions", "--plan", str(plan), "--output", str(output))
        data = read_json(output)
        assert [row["request_id"] for row in data["actions"]] == ["C-1", "C-2", "N-2", "U-1", "U-2", "N-1", "X-1"]
        assert data["meta"]["source_count"] == 7
        assert data["meta"]["action_counts"] == {"call_now": 3, "send_sms": 2, "standard_return": 2}
        assert data["meta"]["owner_counts"] == {"North Desk": 2, "Ops": 2, "Zone": 3}
        assert data["alerts"] == [
            {"alert_id": "A-001", "severity": "critical", "owner": "Ops", "reason": "capacity_exceeded", "request_ids": ["C-1", "C-2"]},
            {"alert_id": "A-002", "severity": "warning", "owner": "Zone", "reason": "unknown_site", "request_ids": ["U-1", "U-2"]},
        ]

    def test_owner_channel_override_and_custom_alert_reasons(self, tmp_path: Path) -> None:
        """Owner-specific channels and alert reasons are data-driven."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["owner_channel_overrides"] = {"Ops": {"send_sms": "pager"}}
        rules["alert_reasons"] = ["capacity_exceeded", "unknown_site", "site_service_blocked"]
        changed = tmp_path / "alert_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        plan = tmp_path / "blocked_plan.json"
        plan.write_text(
            json.dumps({
                "scheduled": [],
                "overflow": [
                    {"request_id": "S-2", "owner": "Ops", "priority": "P2", "reason": "site_service_blocked"},
                    {"request_id": "S-1", "owner": "Ops", "priority": "P1", "reason": "site_service_blocked"},
                    {"request_id": "C-1", "owner": "Ops", "priority": "P1", "reason": "capacity_exceeded"},
                    {"request_id": "X-1", "owner": "Ops", "priority": "P1", "reason": "unknown_service"},
                ],
            }),
            encoding="utf-8",
        )
        output = tmp_path / "override_actions.json"
        run_cli("actions", "--plan", str(plan), "--rules", str(changed), "--output", str(output))
        data = read_json(output)
        assert [row["request_id"] for row in data["actions"]] == ["C-1", "S-1", "S-2", "X-1"]
        by_request = {row["request_id"]: row for row in data["actions"]}
        assert by_request["S-1"]["action"] == "send_sms"
        assert by_request["S-1"]["channel"] == "pager"
        assert by_request["S-2"]["reason_codes"] == ["site_service_blocked"]
        assert by_request["X-1"]["action"] == "standard_return"
        assert data["meta"]["action_counts"] == {"call_now": 1, "send_sms": 2, "standard_return": 1}
        assert data["meta"]["owner_counts"] == {"Ops": 4}
        assert data["alerts"] == [
            {"alert_id": "A-001", "severity": "critical", "owner": "Ops", "reason": "capacity_exceeded", "request_ids": ["C-1"]},
            {"alert_id": "A-002", "severity": "warning", "owner": "Ops", "reason": "site_service_blocked", "request_ids": ["S-1", "S-2"]},
        ]


    def test_reason_action_overrides_change_action_and_severity(self, tmp_path: Path) -> None:
        """Reason action overrides are applied after default overflow mapping."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["reason_action_overrides"] = {
            "site_service_blocked": {"action": "call_now", "severity": "critical"},
            "unknown_service": {"action": "send_sms", "severity": "warning"},
        }
        rules["owner_channel_overrides"] = {"Ops": {"call_now": "pager"}}
        rules["alert_reasons"] = ["site_service_blocked", "unknown_service"]
        changed = tmp_path / "reason_override_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        plan = tmp_path / "reason_override_plan.json"
        plan.write_text(
            json.dumps({
                "scheduled": [{"request_id": "N-1", "priority": "P2", "owner": "North Desk"}],
                "overflow": [
                    {"request_id": "B-1", "owner": "Ops", "priority": "P2", "reason": "site_service_blocked"},
                    {"request_id": "U-1", "owner": "Ops", "priority": "P1", "reason": "unknown_service"},
                ],
            }),
            encoding="utf-8",
        )
        output = tmp_path / "reason_override_actions.json"
        run_cli("actions", "--plan", str(plan), "--rules", str(changed), "--output", str(output))
        data = read_json(output)
        assert [row["request_id"] for row in data["actions"]] == ["B-1", "U-1", "N-1"]
        by_request = {row["request_id"]: row for row in data["actions"]}
        assert by_request["B-1"]["action"] == "call_now"
        assert by_request["B-1"]["severity"] == "critical"
        assert by_request["B-1"]["channel"] == "pager"
        assert by_request["U-1"]["action"] == "send_sms"
        assert by_request["U-1"]["severity"] == "warning"
        assert by_request["U-1"]["channel"] == "sms"
        assert data["meta"]["action_counts"] == {"call_now": 1, "send_sms": 1, "standard_return": 1}
        assert data["meta"]["severity_counts"] == {"critical": 1, "warning": 1, "info": 1}
        assert data["alerts"] == [
            {"alert_id": "A-001", "severity": "critical", "owner": "Ops", "reason": "site_service_blocked", "request_ids": ["B-1"]},
            {"alert_id": "A-002", "severity": "warning", "owner": "Ops", "reason": "unknown_service", "request_ids": ["U-1"]},
        ]

    def test_invalid_reason_action_override_values_fall_back_per_field(self, tmp_path: Path) -> None:
        """Invalid override fields are ignored independently while valid fields still apply."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["reason_action_overrides"] = {
            "site_service_blocked": {"action": "invalid_action", "severity": "urgent"},
            "unknown_service": {"action": "call_now", "severity": "urgent"},
            "unknown_site": {"action": "email", "severity": "critical"},
        }
        rules["alert_reasons"] = ["site_service_blocked", "unknown_service", "unknown_site"]
        changed = tmp_path / "invalid_override_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        plan = tmp_path / "invalid_override_plan.json"
        plan.write_text(
            json.dumps({
                "scheduled": [],
                "overflow": [
                    {"request_id": "INV-1", "owner": "Ops", "priority": "P2", "reason": "site_service_blocked"},
                    {"request_id": "INV-2", "owner": "Ops", "priority": "P2", "reason": "unknown_service"},
                    {"request_id": "INV-3", "owner": "Ops", "priority": "P2", "reason": "unknown_site"},
                ],
            }),
            encoding="utf-8",
        )
        output = tmp_path / "invalid_override_actions.json"
        run_cli("actions", "--plan", str(plan), "--rules", str(changed), "--output", str(output))
        data = read_json(output)
        by_request = {row["request_id"]: row for row in data["actions"]}
        assert by_request["INV-1"]["action"] == "send_sms"
        assert by_request["INV-1"]["severity"] == "warning"
        assert by_request["INV-2"]["action"] == "call_now"
        assert by_request["INV-2"]["severity"] == "info"
        assert by_request["INV-3"]["action"] == "send_sms"
        assert by_request["INV-3"]["severity"] == "critical"
        assert data["meta"]["action_counts"] == {"call_now": 1, "send_sms": 2, "standard_return": 0}
        assert data["meta"]["severity_counts"] == {"critical": 1, "warning": 1, "info": 1}
        assert data["alerts"] == [
            {"alert_id": "A-001", "severity": "critical", "owner": "Ops", "reason": "unknown_site", "request_ids": ["INV-3"]},
            {"alert_id": "A-002", "severity": "warning", "owner": "Ops", "reason": "site_service_blocked", "request_ids": ["INV-1"]},
            {"alert_id": "A-003", "severity": "info", "owner": "Ops", "reason": "unknown_service", "request_ids": ["INV-2"]},
        ]

    def test_absent_or_non_list_alert_reasons_uses_default_capacity_and_unknown_site_only(self, tmp_path: Path) -> None:
        """Absent and non-list alert_reasons both fall back to the two default alert reasons only."""
        base_rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        plan = tmp_path / "default_alert_plan.json"
        plan.write_text(
            json.dumps({
                "scheduled": [{"request_id": "P-1", "priority": "P1", "owner": "Desk"}],
                "overflow": [
                    {"request_id": "C-1", "owner": "Desk", "priority": "P2", "reason": "capacity_exceeded"},
                    {"request_id": "U-1", "owner": "Desk", "priority": "P2", "reason": "unknown_site"},
                    {"request_id": "B-1", "owner": "Desk", "priority": "P2", "reason": "site_service_blocked"},
                    {"request_id": "X-1", "owner": "Desk", "priority": "P2", "reason": "unknown_service"},
                ],
            }),
            encoding="utf-8",
        )
        for marker, alert_value in [("missing", None), ("nonlist", "capacity_exceeded")]:
            rules = dict(base_rules)
            if alert_value is None:
                rules.pop("alert_reasons", None)
            else:
                rules["alert_reasons"] = alert_value
            changed = tmp_path / f"{marker}_alert_rules.json"
            changed.write_text(json.dumps(rules), encoding="utf-8")
            output = tmp_path / f"{marker}_alert_actions.json"
            run_cli("actions", "--plan", str(plan), "--rules", str(changed), "--output", str(output))
            data = read_json(output)
            assert data["alerts"] == [
                {"alert_id": "A-001", "severity": "critical", "owner": "Desk", "reason": "capacity_exceeded", "request_ids": ["C-1"]},
                {"alert_id": "A-002", "severity": "warning", "owner": "Desk", "reason": "unknown_site", "request_ids": ["U-1"]},
            ]
            assert data["meta"]["source_count"] == 5
            assert data["meta"]["action_counts"] == {"call_now": 2, "send_sms": 2, "standard_return": 1}


    def test_urgent_risk_manual_hold_owner_cap_actions_and_replacement(self, tmp_path: Path) -> None:
        """Urgent scheduled rows, manual holds, and owner-cap overflows drive escalations and alert grouping."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["owner_channel_overrides"] = {"Ops": {"call_now": "pager"}}
        rules["alert_reasons"] = ["risk_urgent", "manual_hold", "owner_capacity_exceeded"]
        changed = tmp_path / "risk_action_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        plan = tmp_path / "risk_plan.json"
        plan.write_text(
            json.dumps({
                "scheduled": [
                    {"request_id": "S-urgent", "priority": "P2", "owner": "Ops", "risk_tier": "urgent", "hold_codes": []},
                    {"request_id": "S-p1", "priority": "P1", "owner": "Ops", "risk_tier": "watch", "hold_codes": []},
                ],
                "overflow": [
                    {"request_id": "H-1", "owner": "Ops", "priority": "P2", "reason": "manual_hold", "hold_codes": ["needs_consent", "mobility"]},
                    {"request_id": "O-1", "owner": "Ops", "priority": "P1", "reason": "owner_capacity_exceeded", "hold_codes": []},
                    {"request_id": "U-1", "owner": "Zone", "priority": "P2", "reason": "unknown_site", "hold_codes": []},
                ],
            }),
            encoding="utf-8",
        )
        output = tmp_path / "same" / "m3_actions.json"
        run_cli("actions", "--plan", str(plan), "--rules", str(changed), "--output", str(output))
        first = read_json(output)
        run_cli("actions", "--plan", str(plan), "--rules", str(changed), "--output", str(output))
        data = read_json(output)
        assert data == first
        assert [row["request_id"] for row in data["actions"]] == ["H-1", "O-1", "S-urgent", "S-p1", "U-1"]
        by_id = {row["request_id"]: row for row in data["actions"]}
        assert by_id["S-urgent"] == {"request_id": "S-urgent", "channel": "pager", "action": "call_now", "severity": "critical", "owner": "Ops", "reason_codes": ["risk_urgent"]}
        assert by_id["H-1"]["reason_codes"] == ["manual_hold", "needs_consent", "mobility"]
        assert by_id["H-1"]["channel"] == "pager"
        assert by_id["O-1"]["reason_codes"] == ["owner_capacity_exceeded"]
        assert by_id["S-p1"]["reason_codes"] == ["priority_P1"]
        assert by_id["U-1"]["action"] == "send_sms"
        assert data["meta"]["action_counts"] == {"call_now": 4, "send_sms": 1, "standard_return": 0}
        assert data["meta"]["severity_counts"] == {"critical": 3, "warning": 2, "info": 0}
        assert data["alerts"] == [
            {"alert_id": "A-001", "severity": "critical", "owner": "Ops", "reason": "manual_hold", "request_ids": ["H-1"]},
            {"alert_id": "A-002", "severity": "critical", "owner": "Ops", "reason": "owner_capacity_exceeded", "request_ids": ["O-1"]},
            {"alert_id": "A-003", "severity": "critical", "owner": "Ops", "reason": "risk_urgent", "request_ids": ["S-urgent"]},
        ]
