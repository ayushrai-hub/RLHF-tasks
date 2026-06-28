from __future__ import annotations

import json
from pathlib import Path


def run_cli(*args: str) -> None:
    from clinicflow.cli import main

    result = main(list(args))
    assert result == 0


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestMilestone1:
    def test_cli_integration_normalize_schema_order_counts(self, tmp_path: Path) -> None:
        """Integration path proves schema, ordering, counts, and reject values."""
        output = tmp_path / "nested" / "m1_clean.json"
        run_cli("normalize", "--output", str(output))
        data = read_json(output)
        assert set(data.keys()) == {"accepted", "rejects", "meta"}
        expected_accepted_keys = {"request_id", "patient_id", "service", "priority", "site", "arrival_min", "needs_transport", "triage_score", "risk_tier", "hold_codes"}
        for row in data["accepted"]:
            assert set(row.keys()) == expected_accepted_keys
        for row in data["rejects"]:
            assert set(row.keys()) == {"request_id", "line", "issues"}
        assert set(data["meta"].keys()) == {"source_count", "accepted_count", "rejected_count", "priority_counts", "service_counts", "risk_tier_counts", "hold_count"}
        assert set(data["meta"]["priority_counts"].keys()) == {"P1", "P2", "P3"}
        assert data["meta"]["source_count"] == 9
        assert data["meta"]["accepted_count"] == 6
        assert data["meta"]["rejected_count"] == 3
        assert data["meta"]["priority_counts"] == {"P1": 2, "P2": 3, "P3": 1}
        assert data["meta"]["risk_tier_counts"] == {"urgent": 0, "watch": 2, "routine": 4}
        assert data["meta"]["hold_count"] == 0
        assert [row["request_id"] for row in data["accepted"]] == ["R-100", "R-102", "R-108", "R-107", "R-101", "R-103"]
        assert [row["triage_score"] for row in data["accepted"]] == [43, 39, 24, 22, 22, 15]
        assert [row["risk_tier"] for row in data["accepted"]] == ["watch", "watch", "routine", "routine", "routine", "routine"]
        assert all(row["hold_codes"] == [] for row in data["accepted"])
        assert data["accepted"][0]["needs_transport"] is True
        assert data["rejects"][0] == {"request_id": "R-104", "line": 6, "issues": ["negative"]}

    def test_modified_rules_dependency_mutation_recomputes_score(self, tmp_path: Path) -> None:
        """Modified rules fixture changes a dependency-derived triage_score."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["service_weights"]["lab"] = 9
        changed = tmp_path / "changed_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        output = tmp_path / "changed" / "m1_clean.json"
        run_cli("normalize", "--rules", str(changed), "--output", str(output))
        data = read_json(output)
        lab_row = next(row for row in data["accepted"] if row["request_id"] == "R-107")
        assert lab_row["triage_score"] == 29
        assert data["meta"]["service_counts"] == {"consult": 2, "lab": 3, "xray": 1}
        assert data["meta"]["risk_tier_counts"] == {"urgent": 0, "watch": 2, "routine": 4}
        assert data["meta"]["accepted_count"] == 6

    def test_invalid_edge_branch_missing_malformed_line_values(self, tmp_path: Path) -> None:
        """Invalid edge fixture triggers multi-issue ordering and bool cleanup."""
        csv_path = tmp_path / "bad_rows.csv"
        csv_path.write_text(
            "request_id,patient_id,service,priority,age,arrival_min,needs_transport,site\n"
            "B-0,P-0,lab,P1,65,5, TRUE ,north\n"
            "B-1,,therapy,P1,abc,5,false,north\n"
            "B-2,P-2,lab,P9,50,5,false,north\n"
            "B-3,P-3,lab,P2,abc,5,false,north\n"
            "B-4,P-4,extra,extra,extra,extra,extra,extra,too_many\n",
            encoding="utf-8",
        )
        output = tmp_path / "deep" / "out" / "m1_clean.json"
        run_cli("normalize", "--input", str(csv_path), "--output", str(output))
        data = read_json(output)
        assert output.parent.exists()
        assert data["accepted"][0]["request_id"] == "B-0"
        assert data["accepted"][0]["needs_transport"] is True
        assert data["accepted"][0]["triage_score"] == 40
        assert [item["issues"] for item in data["rejects"]] == [
            ["blank", "non_numeric", "unknown_service"],
            ["invalid_priority"],
            ["non_numeric"],
            ["malformed"],
        ]
        assert [item["line"] for item in data["rejects"]] == [3, 4, 5, 6]
        assert data["rejects"][-1]["request_id"] == "B-4"
        assert data["rejects"][-1]["issues"] == ["malformed"]
        assert data["meta"]["priority_counts"] == {"P1": 1, "P2": 0, "P3": 0}

    def test_disabled_service_and_absent_first_field_malformed(self, tmp_path: Path) -> None:
        """Disabled service and missing first CSV field are separate public branches."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["disabled_services"] = ["lab"]
        changed = tmp_path / "disabled_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        csv_path = tmp_path / "disabled_rows.csv"
        csv_path.write_text(
            "request_id,patient_id,service,priority,age,arrival_min,needs_transport,site\n"
            ",P-x,lab,P1,60\n"
            "D-1,P-1,lab,P1,70,5,false,north\n"
            "D-2,P-2,xray,P2,64,7,false,north\n"
            "T-1,P-t1,xray,P2,64,9,false,north\n"
            "T-0,P-t0,xray,P2,64,9,false,north\n",
            encoding="utf-8",
        )
        output = tmp_path / "m1_disabled.json"
        run_cli("normalize", "--input", str(csv_path), "--rules", str(changed), "--output", str(output))
        data = read_json(output)
        assert [row["request_id"] for row in data["accepted"]] == ["D-2", "T-0", "T-1"]
        assert [row["triage_score"] for row in data["accepted"]] == [25, 25, 25]
        assert data["rejects"] == [
            {"request_id": "", "line": 2, "issues": ["malformed"]},
            {"request_id": "D-1", "line": 3, "issues": ["disabled_service"]},
        ]
        assert data["meta"]["source_count"] == 5
        assert data["meta"]["priority_counts"] == {"P1": 0, "P2": 3, "P3": 0}

    def test_service_alias_site_alias_and_duplicate_request_branch(self, tmp_path: Path) -> None:
        """Aliases canonicalize accepted rows and duplicate accepted ids are rejected."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["service_aliases"] = {"bloodwork": "lab", "imaging": "xray"}
        rules["site_aliases"] = {"clinic-north": "north"}
        changed = tmp_path / "alias_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        csv_path = tmp_path / "alias_rows.csv"
        csv_path.write_text(
            "request_id,patient_id,service,priority,age,arrival_min,needs_transport,site\n"
            "A-1,P-1,bloodwork,P2,45,8,false,clinic-north\n"
            "A-1,P-dup,xray,P1,70,1,true,north\n"
            "A-0,P-0,imaging,P2,45,8,false,clinic-north\n",
            encoding="utf-8",
        )
        output = tmp_path / "alias" / "m1_clean.json"
        run_cli("normalize", "--input", str(csv_path), "--rules", str(changed), "--output", str(output))
        data = read_json(output)
        assert [row["request_id"] for row in data["accepted"]] == ["A-0", "A-1"]
        assert [row["service"] for row in data["accepted"]] == ["xray", "lab"]
        assert [row["site"] for row in data["accepted"]] == ["north", "north"]
        assert [row["triage_score"] for row in data["accepted"]] == [25, 22]
        assert data["rejects"] == [{"request_id": "A-1", "line": 3, "issues": ["duplicate_request"]}]
        assert data["meta"]["service_counts"] == {"lab": 1, "xray": 1}
        assert data["meta"]["priority_counts"] == {"P1": 0, "P2": 2, "P3": 0}


    def test_priority_alias_site_bonus_and_quoted_csv_branch(self, tmp_path: Path) -> None:
        """Priority aliases, quoted CSV fields, and site score bonuses combine."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["service_aliases"] = {"bloodwork": "lab"}
        rules["site_aliases"] = {"north-campus": "north"}
        rules["priority_aliases"] = {"urgent": "P1", "routine": "P3"}
        rules["site_score_bonus"] = {"north": 4}
        changed = tmp_path / "priority_alias_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        csv_path = tmp_path / "quoted_rows.csv"
        csv_path.write_text(
            "request_id,patient_id,service,priority,age,arrival_min,needs_transport,site\n"
            "Q-2,P-2,bloodwork,routine,40,3,false,north-campus\n"
            'Q-1,"P,1",bloodwork,urgent,65,3,true,north-campus\n',
            encoding="utf-8",
        )
        output = tmp_path / "quoted" / "m1_clean.json"
        run_cli("normalize", "--input", str(csv_path), "--rules", str(changed), "--output", str(output))
        data = read_json(output)
        assert [row["request_id"] for row in data["accepted"]] == ["Q-1", "Q-2"]
        assert data["accepted"][0]["patient_id"] == "P,1"
        assert [row["priority"] for row in data["accepted"]] == ["P1", "P3"]
        assert [row["service"] for row in data["accepted"]] == ["lab", "lab"]
        assert [row["site"] for row in data["accepted"]] == ["north", "north"]
        assert [row["triage_score"] for row in data["accepted"]] == [44, 16]
        assert data["rejects"] == []
        assert data["meta"]["priority_counts"] == {"P1": 1, "P2": 0, "P3": 1}

    def test_rejected_duplicate_id_does_not_block_later_valid_acceptance(self, tmp_path: Path) -> None:
        """Rejected request ids are not remembered as duplicates, and duplicate is checked only after other validation passes."""
        csv_path = tmp_path / "duplicate_validation_rows.csv"
        csv_path.write_text(
            "request_id,patient_id,service,priority,age,arrival_min,needs_transport,site\n"
            "DUP-1,P-bad,ghost,P1,50,5,false,north\n"
            "DUP-1,P-good,lab,P2,50,5,false,north\n"
            "DUP-1,P-late,lab,P9,50,5,false,north\n"
            "DUP-2,P-ok,xray,P2,64,1,false,north\n"
            "DUP-2,,ghost,P9,abc,-7,maybe,north\n",
            encoding="utf-8",
        )
        output = tmp_path / "m1_duplicate_validation.json"
        run_cli("normalize", "--input", str(csv_path), "--output", str(output))
        data = read_json(output)
        assert [row["request_id"] for row in data["accepted"]] == ["DUP-2", "DUP-1"]
        assert data["accepted"][0]["triage_score"] == 25
        assert data["accepted"][1]["triage_score"] == 22
        assert data["rejects"] == [
            {"request_id": "DUP-1", "line": 2, "issues": ["unknown_service"]},
            {"request_id": "DUP-1", "line": 4, "issues": ["invalid_priority"]},
            {"request_id": "DUP-2", "line": 6, "issues": ["blank", "non_numeric", "negative", "unknown_service", "invalid_priority"]},
        ]
        assert data["meta"]["source_count"] == 5
        assert data["meta"]["priority_counts"] == {"P1": 0, "P2": 2, "P3": 0}


    def test_patient_flags_hold_codes_risk_tiers_and_default_replacement(self, tmp_path: Path) -> None:
        """Patient flags add score, derive hold codes, tier risk, and repeated default writes replace output."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["patient_flags"] = {"P-flag": ["mobility", "needs_consent", "mobility"], "P-ok": ["transport_gap"]}
        rules["flag_score_bonus"] = {"mobility": 4, "needs_consent": 8, "transport_gap": 2}
        rules["hold_flags"] = ["needs_consent", "transport_gap"]
        rules["risk_tier_thresholds"] = {"urgent": 42, "watch": 25}
        changed = tmp_path / "risk_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        csv_path = tmp_path / "risk_rows.csv"
        csv_path.write_text(
            "request_id,patient_id,service,priority,age,arrival_min,needs_transport,site\n"
            "F-2,P-ok,lab,P2,40,5,false,north\n"
            "F-1,P-flag,xray,P1,66,4,true,north\n"
            "F-3,P-clear,consult,P3,30,6,false,north\n",
            encoding="utf-8",
        )
        output = tmp_path / "risk" / "m1_clean.json"
        run_cli("normalize", "--input", str(csv_path), "--rules", str(changed), "--output", str(output))
        data = read_json(output)
        assert [row["request_id"] for row in data["accepted"]] == ["F-1", "F-2", "F-3"]
        by_id = {row["request_id"]: row for row in data["accepted"]}
        assert by_id["F-1"]["triage_score"] == 59
        assert by_id["F-1"]["risk_tier"] == "urgent"
        assert by_id["F-1"]["hold_codes"] == ["needs_consent"]
        assert by_id["F-2"]["triage_score"] == 24
        assert by_id["F-2"]["risk_tier"] == "routine"
        assert by_id["F-2"]["hold_codes"] == ["transport_gap"]
        assert data["meta"]["risk_tier_counts"] == {"urgent": 1, "watch": 0, "routine": 2}
        assert data["meta"]["hold_count"] == 2

        default_output = Path("/app/output/m1_clean.json")
        default_output.parent.mkdir(parents=True, exist_ok=True)
        default_output.write_text("stale", encoding="utf-8")
        run_cli("normalize", "--input", str(csv_path), "--rules", str(changed))
        first = read_json(default_output)
        run_cli("normalize", "--input", str(csv_path), "--rules", str(changed))
        assert read_json(default_output) == first
        assert first["meta"]["accepted_count"] == 3

    def test_flag_fallbacks_deduped_hold_codes_and_invalid_bonus_values(self, tmp_path: Path) -> None:
        """Duplicate hold flags are deduped while non-list patient flags and invalid bonuses safely fallback."""
        rules = json.loads(Path("/app/data/service_rules.json").read_text(encoding="utf-8"))
        rules["patient_flags"] = {"P-dup": ["mobility", "mobility", "needs_consent"], "P-bad": "not-a-list", "P-invalid": ["bad_bonus"]}
        rules["flag_score_bonus"] = {"mobility": 4, "needs_consent": 8, "bad_bonus": "not-int"}
        rules["hold_flags"] = ["mobility", "needs_consent", "bad_bonus"]
        rules["risk_tier_thresholds"] = {"urgent": 42, "watch": 25}
        changed = tmp_path / "flag_fallback_rules.json"
        changed.write_text(json.dumps(rules), encoding="utf-8")
        csv_path = tmp_path / "flag_fallback_rows.csv"
        csv_path.write_text(
            "request_id,patient_id,service,priority,age,arrival_min,needs_transport,site\n"
            "HF-1,P-dup,xray,P1,66,1,true,north\n"
            "HF-2,P-bad,lab,P2,40,2,false,north\n"
            "HF-3,P-invalid,lab,P2,40,3,false,north\n",
            encoding="utf-8",
        )
        output = tmp_path / "flag_fallback_clean.json"
        run_cli("normalize", "--input", str(csv_path), "--rules", str(changed), "--output", str(output))
        data = read_json(output)
        by_id = {row["request_id"]: row for row in data["accepted"]}
        assert by_id["HF-1"]["hold_codes"] == ["mobility", "needs_consent"]
        assert by_id["HF-1"]["triage_score"] == 59
        assert by_id["HF-2"]["hold_codes"] == []
        assert by_id["HF-2"]["triage_score"] == 22
        assert by_id["HF-3"]["hold_codes"] == ["bad_bonus"]
        assert by_id["HF-3"]["triage_score"] == 22
        assert data["meta"]["hold_count"] == 2
