from __future__ import annotations

import json
from pathlib import Path


def run_cli(*args: str) -> None:
    from clinicflow.cli import main

    result = main(list(args))
    assert result == 0


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


EMPTY_PLAN = {
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


class TestMilestone2:
    def test_cli_integration_plan_schema_capacity_order_counts(self, tmp_path: Path) -> None:
        """Integration path proves plan schema, capacity_used, and ordering."""
        clean = tmp_path / "m1_clean.json"
        plan = tmp_path / "deep" / "m2_plan.json"
        run_cli("normalize", "--output", str(clean))
        clean_before = clean.read_text(encoding="utf-8")
        run_cli("plan", "--clean", str(clean), "--output", str(plan))
        assert clean.read_text(encoding="utf-8") == clean_before
        data = read_json(plan)
        assert set(data.keys()) == {"scheduled", "overflow", "meta"}
        expected_scheduled_keys = {"request_id", "site_id", "owner", "service", "priority", "slot_start", "slot_end", "overflow", "risk_tier", "hold_codes"}
        expected_overflow_keys = {"request_id", "site_id", "owner", "reason", "priority", "duration", "risk_tier", "hold_codes"}
        for row in data["scheduled"]:
            assert set(row.keys()) == expected_scheduled_keys
        for row in data["overflow"]:
            assert set(row.keys()) == expected_overflow_keys
        assert set(data["meta"].keys()) == {"source_count", "scheduled_count", "overflow_count", "owner_counts", "capacity_used", "owner_capacity_used"}
        assert data["meta"]["source_count"] == 6
        assert data["meta"]["scheduled_count"] == 4
        assert data["meta"]["overflow_count"] == 2
        assert data["meta"]["capacity_used"] == {"north": 45, "south": 15, "unknown": 0, "west": 25}
        assert data["meta"]["owner_capacity_used"] == {"North Desk": 45, "South Desk": 15, "West Desk": 25}
        assert [row["request_id"] for row in data["scheduled"]] == ["R-100", "R-101", "R-103", "R-102"]
        north_rows = [row for row in data["scheduled"] if row["site_id"] == "north"]
        assert [(row["request_id"], row["slot_start"], row["slot_end"]) for row in north_rows] == [("R-100", 0, 30), ("R-101", 30, 45)]
        assert all(row["overflow"] is False for row in data["scheduled"])
        assert [row["reason"] for row in data["overflow"]] == ["capacity_exceeded", "unknown_site"]

    def test_modified_capacity_dependency_mutation_recomputes_overflow(self, tmp_path: Path) -> None:
        """Modified capacity dependency moves one request from overflow to scheduled."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["site_capacity"]["north"] = 80
        changed = tmp_path / "modified_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        clean = tmp_path / "m1_clean.json"
        plan = tmp_path / "m2_plan.json"
        run_cli("normalize", "--rules", str(changed), "--output", str(clean))
        run_cli("plan", "--clean", str(clean), "--rules", str(changed), "--output", str(plan))
        data = read_json(plan)
        assert "R-108" in [row["request_id"] for row in data["scheduled"]]
        assert data["meta"]["capacity_used"]["north"] == 70
        assert data["meta"]["overflow_count"] == 1
        assert data["overflow"][0]["reason"] == "unknown_site"

    def test_unknown_fallback_edge_branch_unassigned_capacity_zero(self, tmp_path: Path) -> None:
        """Unknown site fallback creates unassigned owner and zero capacity_used."""
        clean = tmp_path / "m1_clean.json"
        plan = tmp_path / "m2_plan.json"
        run_cli("normalize", "--output", str(clean))
        run_cli("plan", "--clean", str(clean), "--output", str(plan))
        data = read_json(plan)
        unknown = next(row for row in data["overflow"] if row["request_id"] == "R-107")
        assert unknown["site_id"] == "unknown"
        assert unknown["owner"] == "unassigned"
        assert unknown["reason"] == "unknown_site"
        assert unknown["duration"] == 15
        assert data["meta"]["owner_counts"] == {"North Desk": 3, "South Desk": 1, "West Desk": 1, "unassigned": 1}
        assert data["meta"]["capacity_used"]["unknown"] == 0
        assert data["meta"]["owner_capacity_used"] == {"North Desk": 45, "South Desk": 15, "West Desk": 25}

        custom_clean = tmp_path / "custom_clean.json"
        custom_clean.write_text(
            json.dumps({"accepted": [{"request_id": "U-1", "service": "therapy", "priority": "P2", "site": "north"}]}),
            encoding="utf-8",
        )
        custom_plan = tmp_path / "custom_plan.json"
        run_cli("plan", "--clean", str(custom_clean), "--output", str(custom_plan))
        custom_data = read_json(custom_plan)
        assert custom_data["overflow"][0]["reason"] == "unknown_service"
        assert custom_data["overflow"][0]["duration"] == 0

        missing_plan = tmp_path / "missing_plan.json"
        run_cli("plan", "--clean", str(tmp_path / "missing_clean.json"), "--output", str(missing_plan))
        assert read_json(missing_plan) == EMPTY_PLAN

        malformed_clean = tmp_path / "malformed_clean.json"
        malformed_clean.write_text("not json{{", encoding="utf-8")
        malformed_plan = tmp_path / "malformed_plan.json"
        run_cli("plan", "--clean", str(malformed_clean), "--output", str(malformed_plan))
        assert read_json(malformed_plan) == EMPTY_PLAN

        no_list_clean = tmp_path / "no_list_clean.json"
        no_list_clean.write_text(json.dumps({"accepted": 42}), encoding="utf-8")
        no_list_plan = tmp_path / "no_list_plan.json"
        run_cli("plan", "--clean", str(no_list_clean), "--output", str(no_list_plan))
        assert read_json(no_list_plan) == EMPTY_PLAN

        no_key_clean = tmp_path / "no_key_clean.json"
        no_key_clean.write_text(json.dumps({"other": []}), encoding="utf-8")
        no_key_plan = tmp_path / "no_key_plan.json"
        run_cli("plan", "--clean", str(no_key_clean), "--output", str(no_key_plan))
        assert read_json(no_key_plan) == EMPTY_PLAN

    def test_site_start_offsets_and_overflow_tie_collisions(self, tmp_path: Path) -> None:
        """Site start offsets affect slots while overflow tie-breakers stay deterministic."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["site_start_min"] = {"north": 100, "west": 5}
        rules["site_capacity"]["north"] = 45
        changed = tmp_path / "offset_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        clean = tmp_path / "offset_clean.json"
        clean.write_text(
            json.dumps({
                "accepted": [
                    {"request_id": "Q-2", "service": "xray", "priority": "P2", "site": "north"},
                    {"request_id": "Q-1", "service": "lab", "priority": "P1", "site": "north"},
                    {"request_id": "Q-3", "service": "consult", "priority": "P2", "site": "west"},
                    {"request_id": "Q-4", "service": "lab", "priority": "P1", "site": "north"},
                ]
            }),
            encoding="utf-8",
        )
        plan = tmp_path / "offset_plan.json"
        run_cli("plan", "--clean", str(clean), "--rules", str(changed), "--output", str(plan))
        data = read_json(plan)
        assert [(row["request_id"], row["slot_start"], row["slot_end"]) for row in data["scheduled"]] == [
            ("Q-2", 100, 130),
            ("Q-1", 130, 145),
            ("Q-3", 5, 30),
        ]
        assert data["meta"]["capacity_used"] == {"north": 45, "south": 0, "unknown": 0, "west": 25}
        assert [(row["request_id"], row["site_id"], row["owner"], row["reason"], row["priority"], row["duration"], row["risk_tier"], row["hold_codes"]) for row in data["overflow"]] == [
            ("Q-4", "north", "North Desk", "capacity_exceeded", "P1", 15, "routine", [])
        ]

        tie_rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        tie_rules["site_capacity"]["north"] = 0
        tie_rules_path = tmp_path / "tie_rules.json"
        tie_rules_path.write_text(json.dumps(tie_rules), encoding="utf-8")
        tie_clean = tmp_path / "tie_clean.json"
        tie_clean.write_text(
            json.dumps({
                "accepted": [
                    {"request_id": "Z-2", "service": "lab", "priority": "P2", "site": "north"},
                    {"request_id": "A-9", "service": "lab", "priority": "P1", "site": "north"},
                    {"request_id": "Z-1", "service": "lab", "priority": "P2", "site": "north"},
                ]
            }),
            encoding="utf-8",
        )
        tie_plan = tmp_path / "tie_plan.json"
        run_cli("plan", "--clean", str(tie_clean), "--rules", str(tie_rules_path), "--output", str(tie_plan))
        tie_data = read_json(tie_plan)
        assert [row["request_id"] for row in tie_data["overflow"]] == ["A-9", "Z-1", "Z-2"]
        assert [row["reason"] for row in tie_data["overflow"]] == ["capacity_exceeded", "capacity_exceeded", "capacity_exceeded"]

    def test_service_buffer_site_block_and_priority_reserve(self, tmp_path: Path) -> None:
        """Buffers, blocked services, and P1 reserve interact with capacity."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["site_capacity"] = {"north": 30, "south": 20}
        rules["site_owner"] = {"north": "North Desk", "south": "South Desk"}
        rules["durations"] = {"lab": 10, "xray": 20, "consult": 25}
        rules["service_buffer_min"] = {"lab": 5}
        rules["site_start_min"] = {"north": 100, "south": 0}
        rules["site_service_blocks"] = {"north": ["xray"]}
        rules["priority_capacity_reserve"] = {"north": 10}
        changed = tmp_path / "buffer_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        clean = tmp_path / "buffer_clean.json"
        clean.write_text(
            json.dumps({
                "accepted": [
                    {"request_id": "S-1", "service": "lab", "priority": "P2", "site": "north"},
                    {"request_id": "S-2", "service": "lab", "priority": "P2", "site": "north"},
                    {"request_id": "S-3", "service": "xray", "priority": "P1", "site": "north"},
                    {"request_id": "S-4", "service": "lab", "priority": "P1", "site": "north"},
                ]
            }),
            encoding="utf-8",
        )
        plan = tmp_path / "buffer_plan.json"
        run_cli("plan", "--clean", str(clean), "--rules", str(changed), "--output", str(plan))
        data = read_json(plan)
        assert [(row["request_id"], row["slot_start"], row["slot_end"]) for row in data["scheduled"]] == [
            ("S-1", 100, 115),
            ("S-4", 115, 130),
        ]
        assert [(row["request_id"], row["site_id"], row["owner"], row["reason"], row["priority"], row["duration"]) for row in data["overflow"]] == [
            ("S-2", "north", "North Desk", "capacity_exceeded", "P2", 15),
            ("S-3", "north", "North Desk", "site_service_blocked", "P1", 20),
        ]
        assert data["meta"]["capacity_used"] == {"north": 30, "south": 0, "unknown": 0}
        assert data["meta"]["owner_counts"] == {"North Desk": 4}


    def test_site_service_duration_override_and_buffer_capacity(self, tmp_path: Path) -> None:
        """Site-specific duration overrides are applied before service buffers."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["site_capacity"] = {"north": 40, "south": 10, "west": 25}
        rules["site_owner"] = {"north": "North Desk", "south": "South Desk", "west": "West Desk"}
        rules["durations"] = {"lab": 15, "xray": 30, "consult": 25}
        rules["service_buffer_min"] = {"lab": 3}
        rules["site_service_duration_overrides"] = {"north": {"lab": 22}, "west": {"lab": 7}}
        rules["site_start_min"] = {"north": 10, "west": 5, "south": 0}
        changed = tmp_path / "duration_override_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        clean = tmp_path / "override_clean.json"
        clean.write_text(
            json.dumps({
                "accepted": [
                    {"request_id": "O-1", "service": "lab", "priority": "P2", "site": "north"},
                    {"request_id": "O-2", "service": "xray", "priority": "P1", "site": "north"},
                    {"request_id": "O-3", "service": "lab", "priority": "P3", "site": "west"},
                ]
            }),
            encoding="utf-8",
        )
        plan = tmp_path / "duration_override_plan.json"
        run_cli("plan", "--clean", str(clean), "--rules", str(changed), "--output", str(plan))
        data = read_json(plan)
        assert [(row["request_id"], row["slot_start"], row["slot_end"]) for row in data["scheduled"]] == [("O-1", 10, 35), ("O-3", 5, 15)]
        assert [(row["request_id"], row["site_id"], row["owner"], row["reason"], row["priority"], row["duration"]) for row in data["overflow"]] == [
            ("O-2", "north", "North Desk", "capacity_exceeded", "P1", 30)
        ]
        assert data["meta"]["capacity_used"] == {"north": 25, "south": 0, "unknown": 0, "west": 10}
        assert data["meta"]["owner_counts"] == {"North Desk": 2, "West Desk": 1}

    def test_interleaved_processing_order_reserve_and_final_sort_are_separate(self, tmp_path: Path) -> None:
        """Planning consumes capacity in accepted-list order even though final rows are sorted for output."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["site_capacity"] = {"north": 40, "west": 25}
        rules["site_owner"] = {"north": "North Desk", "west": "West Desk"}
        rules["durations"] = {"lab": 10, "consult": 25, "xray": 20}
        rules["service_buffer_min"] = {"lab": 5}
        rules["priority_capacity_reserve"] = {"north": 20}
        changed = tmp_path / "interleaved_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        clean = tmp_path / "interleaved_clean.json"
        clean.write_text(
            json.dumps({
                "accepted": [
                    {"request_id": "I-3", "service": "lab", "priority": "P2", "site": "north"},
                    {"request_id": "I-2", "service": "consult", "priority": "P2", "site": "north"},
                    {"request_id": "I-1", "service": "xray", "priority": "P1", "site": "north"},
                    {"request_id": "I-4", "service": "lab", "priority": "P2", "site": "west"},
                    {"request_id": "I-5", "service": "consult", "priority": "P1", "site": "north"},
                ]
            }),
            encoding="utf-8",
        )
        plan = tmp_path / "interleaved_plan.json"
        run_cli("plan", "--clean", str(clean), "--rules", str(changed), "--output", str(plan))
        data = read_json(plan)
        assert [(row["request_id"], row["site_id"], row["slot_start"], row["slot_end"]) for row in data["scheduled"]] == [
            ("I-3", "north", 0, 15),
            ("I-1", "north", 15, 35),
            ("I-4", "west", 0, 15),
        ]
        assert [(row["request_id"], row["priority"], row["reason"], row["duration"]) for row in data["overflow"]] == [
            ("I-5", "P1", "capacity_exceeded", 25),
            ("I-2", "P2", "capacity_exceeded", 25),
        ]
        assert data["meta"]["capacity_used"] == {"north": 35, "unknown": 0, "west": 15}
        assert data["meta"]["owner_counts"] == {"North Desk": 4, "West Desk": 1}


    def test_risk_buffers_manual_holds_owner_caps_and_repeated_replacement(self, tmp_path: Path) -> None:
        """Risk buffers, manual holds, and owner-wide capacity caps cascade from clean rows into plan state."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["site_capacity"] = {"north": 80, "west": 60}
        rules["site_owner"] = {"north": "Shared Desk", "west": "Shared Desk"}
        rules["durations"] = {"lab": 10, "xray": 20, "consult": 15}
        rules["risk_tier_buffer_min"] = {"urgent": 7, "watch": 3}
        rules["owner_capacity_cap"] = {"Shared Desk": 50}
        changed = tmp_path / "risk_plan_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        clean = tmp_path / "risk_clean.json"
        clean.write_text(
            json.dumps({
                "accepted": [
                    {"request_id": "C-1", "service": "xray", "priority": "P1", "site": "north", "risk_tier": "urgent", "hold_codes": []},
                    {"request_id": "C-2", "service": "lab", "priority": "P2", "site": "west", "risk_tier": "watch", "hold_codes": []},
                    {"request_id": "C-3", "service": "consult", "priority": "P2", "site": "north", "risk_tier": "urgent", "hold_codes": ["needs_consent"]},
                    {"request_id": "C-4", "service": "lab", "priority": "P1", "site": "west", "risk_tier": "urgent", "hold_codes": []},
                    {"request_id": "C-5", "service": "lab", "priority": "P1", "site": "north", "risk_tier": "unknown", "hold_codes": "bad"},
                ]
            }),
            encoding="utf-8",
        )
        plan = tmp_path / "same" / "m2_plan.json"
        run_cli("plan", "--clean", str(clean), "--rules", str(changed), "--output", str(plan))
        first = read_json(plan)
        run_cli("plan", "--clean", str(clean), "--rules", str(changed), "--output", str(plan))
        data = read_json(plan)
        assert data == first
        assert [(row["request_id"], row["slot_start"], row["slot_end"], row["risk_tier"], row["hold_codes"]) for row in data["scheduled"]] == [
            ("C-1", 0, 27, "urgent", []),
            ("C-5", 27, 37, "routine", []),
            ("C-2", 0, 13, "watch", []),
        ]
        assert [(row["request_id"], row["reason"], row["duration"], row["risk_tier"], row["hold_codes"]) for row in data["overflow"]] == [
            ("C-3", "manual_hold", 22, "urgent", ["needs_consent"]),
            ("C-4", "owner_capacity_exceeded", 17, "urgent", []),
        ]
        assert data["meta"]["capacity_used"] == {"north": 37, "unknown": 0, "west": 13}
        assert data["meta"]["owner_capacity_used"] == {"Shared Desk": 50}
        assert data["meta"]["owner_counts"] == {"Shared Desk": 5}

    def test_owner_capacity_used_includes_zero_scheduled_cap_owner(self, tmp_path: Path) -> None:
        """owner_capacity_used keeps configured cap owners even when they have no scheduled minutes."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["owner_capacity_cap"] = {"Idle Desk": 100, "North Desk": 40}
        changed = tmp_path / "idle_owner_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        clean = tmp_path / "m1_clean.json"
        plan = tmp_path / "m2_plan.json"
        run_cli("normalize", "--rules", str(changed), "--output", str(clean))
        run_cli("plan", "--clean", str(clean), "--rules", str(changed), "--output", str(plan))
        data = read_json(plan)
        assert data["meta"]["owner_capacity_used"]["Idle Desk"] == 0
        assert data["meta"]["owner_capacity_used"]["North Desk"] == 30
        assert "Idle Desk" not in data["meta"]["owner_counts"]
