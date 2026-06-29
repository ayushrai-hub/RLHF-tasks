"""Verifier for migration-safe fix planning."""

import json
import subprocess

CP = "/app/build/pubgate.jar:/usr/share/java/gson.jar:/usr/share/java/sqlite-jdbc.jar:/usr/share/java/kotlin-stdlib.jar:/usr/share/java/kotlin-stdlib-jdk7.jar:/usr/share/java/kotlin-stdlib-jdk8.jar"
MAIN = "com.terminus.pubgate.MainKt"
BUILT = False


def build_app():
    global BUILT
    if not BUILT:
        subprocess.run(["/app/build.sh"], cwd="/app", check=True)
        BUILT = True


def run_cli(*args):
    build_app()
    proc = subprocess.run(["java", "-cp", CP, MAIN, *args], cwd="/app", text=True, capture_output=True)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    return proc


def write_runtime_validation(tmp_path):
    validation = tmp_path / "validation.json"
    validation.write_text(json.dumps({
        "summary": {"subscriptions": 1, "checkedTables": 2, "compatible": 0, "blocked": 2, "diagnostics": 3},
        "results": [
            {"subscription": "sub_ops", "publication": "ops_pub", "table": "ops.events", "status": "blocked", "publishedColumns": [], "subscriberColumns": ["event_id", "payload"], "diagnostics": [
                {"code": "missing_table", "severity": "blocking", "message": "ops.events is not in publication ops_pub"}
            ]},
            {"subscription": "sub_ops", "publication": "ops_pub", "table": "ops.widgets", "status": "blocked", "publishedColumns": ["owner_id"], "subscriberColumns": ["widget_id", "ghost_col"], "diagnostics": [
                {"code": "missing_column", "severity": "blocking", "message": "ghost_col is absent from publisher table", "missingColumns": ["ghost_col"]},
                {"code": "unsafe_filter", "severity": "blocking", "message": "publication filter omits subscriber columns", "missingColumns": ["widget_id"]}
            ]},
            {"subscription": "sub_ops", "publication": "missing_pub", "table": "ops.widgets", "status": "blocked", "publishedColumns": [], "subscriberColumns": ["widget_id"], "diagnostics": [
                {"code": "missing_publication", "severity": "blocking", "message": "missing_pub is not present in the publisher snapshot"}
            ]}
        ]
    }) + "\n")
    return validation


def plan_runtime_validation(tmp_path):
    validation = write_runtime_validation(tmp_path)
    out = tmp_path / "out" / "plan.json"
    sql = tmp_path / "out" / "plan.sql"
    run_cli("plan", "--validation", str(validation), "--out", str(out), "--sql", str(sql))
    return json.loads(out.read_text()), sql.read_text()


class TestMilestone3:
    def test_plan_public_fixture_writes_json_and_sql_actions(self, tmp_path):
        """plan creates deterministic SQL for fixable filters and review actions for identity-full blockers."""
        catalog = tmp_path / "catalog.json"
        validation = tmp_path / "validation.json"
        plan = tmp_path / "nested" / "plan.json"
        sql = tmp_path / "nested" / "plan.sql"
        run_cli("parse", "--schema", "/app/input/publisher_schema.sql", "--publications", "/app/input/publications.sql", "--subscriptions", "/app/input/subscriptions.json", "--db", str(tmp_path / "c.db"), "--out", str(catalog))
        run_cli("validate", "--catalog", str(catalog), "--out", str(validation))
        run_cli("plan", "--validation", str(validation), "--out", str(plan), "--sql", str(sql))
        data = json.loads(plan.read_text())
        assert plan.read_text().endswith("\n")
        assert data["summary"] == {"actions": 2, "blockingActions": 1, "reviewActions": 1}
        assert [a["type"] for a in data["actions"]] == ["widen_column_filter", "review_replica_identity"]
        widen = data["actions"][0]
        assert widen["columns"] == ["account_id", "id", "state", "total_cents"]
        assert widen["sql"] == "ALTER PUBLICATION app_pub SET TABLE public.orders (account_id, id, state, total_cents);"
        review = data["actions"][1]
        assert review["severity"] == "review"
        assert review["sql"] == ""
        assert sql.read_text() == "ALTER PUBLICATION app_pub SET TABLE public.orders (account_id, id, state, total_cents);\n"

    def test_plan_runtime_validation_action_order_and_review_only_schema_gap(self, tmp_path):
        """runtime diagnostics map to blocking SQL actions before review-only schema actions."""
        data, _ = plan_runtime_validation(tmp_path)
        assert [a["type"] for a in data["actions"]] == [
            "add_table_to_publication",
            "widen_column_filter",
            "create_publication_review",
            "review_schema_gap",
        ]
        assert data["actions"][2]["sql"] == ""
        assert data["actions"][3]["sql"] == ""

    def test_plan_runtime_missing_table_sql_uses_bare_table_without_column_list(self, tmp_path):
        """missing_table actions add the table with bare identifiers and no column list."""
        data, _ = plan_runtime_validation(tmp_path)
        assert data["actions"][0]["sql"] == "ALTER PUBLICATION ops_pub ADD TABLE ops.events;"

    def test_plan_runtime_widen_filter_excludes_schema_missing_columns(self, tmp_path):
        """widen_column_filter includes published and publisher-backed missing columns, not schema gaps."""
        data, sql_text = plan_runtime_validation(tmp_path)
        assert data["actions"][1]["sql"] == "ALTER PUBLICATION ops_pub SET TABLE ops.widgets (owner_id, widget_id);"
        assert "ghost_col" not in data["actions"][1]["columns"]
        assert sql_text.splitlines() == [
            "ALTER PUBLICATION ops_pub ADD TABLE ops.events;",
            "ALTER PUBLICATION ops_pub SET TABLE ops.widgets (owner_id, widget_id);",
        ]

    def test_plan_merges_multiple_widening_diagnostics_for_one_filter(self, tmp_path):
        """unsafe_filter and primary_key_omitted produce one widened filter action with a union of columns."""
        validation = tmp_path / "validation.json"
        validation.write_text(json.dumps({
            "summary": {"subscriptions": 1, "checkedTables": 1, "compatible": 0, "blocked": 1, "diagnostics": 2},
            "results": [
                {"subscription": "sub_ops", "publication": "ops_pub", "table": "ops.widgets", "status": "blocked", "publishedColumns": ["owner_id"], "subscriberColumns": ["widget_id", "color"], "diagnostics": [
                    {"code": "unsafe_filter", "severity": "blocking", "message": "publication filter omits subscriber columns", "missingColumns": ["color"]},
                    {"code": "primary_key_omitted", "severity": "blocking", "message": "publication filter omits primary key columns", "missingColumns": ["widget_id"]}
                ]}
            ]
        }) + "\n")
        out = tmp_path / "plan.json"
        sql = tmp_path / "plan.sql"
        run_cli("plan", "--validation", str(validation), "--out", str(out), "--sql", str(sql))
        data = json.loads(out.read_text())
        assert data["summary"] == {"actions": 1, "blockingActions": 1, "reviewActions": 0}
        assert data["actions"][0]["type"] == "widen_column_filter"
        assert data["actions"][0]["columns"] == ["color", "owner_id", "widget_id"]
        assert sql.read_text() == "ALTER PUBLICATION ops_pub SET TABLE ops.widgets (color, owner_id, widget_id);\n"
