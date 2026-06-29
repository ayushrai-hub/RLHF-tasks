"""Verifier for column-filter compatibility validation."""

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


def make_catalog(tmp_path):
    catalog = tmp_path / "catalog.json"
    db = tmp_path / "catalog.db"
    run_cli(
        "parse",
        "--schema", "/app/input/publisher_schema.sql",
        "--publications", "/app/input/publications.sql",
        "--subscriptions", "/app/input/subscriptions.json",
        "--db", str(db),
        "--out", str(catalog),
    )
    return catalog


def validate_public_fixture(tmp_path):
    catalog = make_catalog(tmp_path)
    out = tmp_path / "reports" / "validation.json"
    run_cli("validate", "--catalog", str(catalog), "--out", str(out))
    data = json.loads(out.read_text())
    return data


def write_runtime_edge_catalog(tmp_path):
    catalog = tmp_path / "catalog.json"
    catalog.write_text(json.dumps({
        "tables": [
            {"schema": "ops", "name": "widgets", "replicaIdentity": "default", "columns": [
                {"name": "widget_id", "type": "uuid", "nullable": False, "primaryKey": True},
                {"name": "owner_id", "type": "uuid", "nullable": False, "primaryKey": False}
            ]}
        ],
        "publications": [
            {"name": "widget_pub", "tables": [
                {"schema": "ops", "name": "widgets", "columns": ["owner_id"]}
            ]}
        ],
        "subscriptions": [
            {"name": "sub_missing_pub", "publication": "missing_pub", "targetTables": [
                {"schema": "ops", "name": "widgets", "columns": ["widget_id"]}
            ]},
            {"name": "sub_widgets", "publication": "widget_pub", "targetTables": [
                {"schema": "ops", "name": "widgets", "columns": ["widget_id", "ghost_col"]}
            ]},
            {"name": "sub_ghost", "publication": "widget_pub", "targetTables": [
                {"schema": "ops", "name": "phantoms", "columns": ["id"]}
            ]}
        ]
    }) + "\n")
    return catalog


def validate_runtime_edge_catalog(tmp_path):
    catalog = write_runtime_edge_catalog(tmp_path)
    out = tmp_path / "validation.json"
    run_cli("validate", "--catalog", str(catalog), "--out", str(out))
    return json.loads(out.read_text())


def assert_diagnostic_contract(diag, code, message_substring=None, missing_columns=None):
    assert diag["code"] == code
    assert diag["severity"] == "blocking"
    assert isinstance(diag["message"], str)
    assert diag["message"].strip()
    if message_substring is not None:
        assert message_substring in diag["message"]
    if missing_columns is None:
        assert "missingColumns" not in diag
    else:
        assert diag["missingColumns"] == missing_columns


class TestMilestone2:
    def test_validate_public_fixture_summary_and_compatible_row(self, tmp_path):
        """validate writes the public fixture report shape, summary, and compatible table row."""
        data = validate_public_fixture(tmp_path)
        assert list(data.keys()) == ["summary", "results"]
        assert data["summary"] == {"subscriptions": 2, "checkedTables": 3, "compatible": 1, "blocked": 2, "diagnostics": 2}
        assert [(r["subscription"], r["table"], r["publication"]) for r in data["results"]] == sorted(
            (r["subscription"], r["table"], r["publication"]) for r in data["results"]
        )
        by_table = {r["table"]: r for r in data["results"]}
        acct = by_table["public.accounts"]
        assert list(acct.keys()) == ["subscription", "publication", "table", "status", "publishedColumns", "subscriberColumns", "diagnostics"]
        assert acct["status"] == "compatible"
        assert acct["publishedColumns"] == ["email", "id", "status"]
        assert acct["subscriberColumns"] == ["email", "id", "status"]
        assert acct["diagnostics"] == []
        assert by_table["public.orders"]["status"] == "blocked"
        assert by_table["public.audit_log"]["status"] == "blocked"

    def test_validate_public_fixture_reports_unsafe_filter_missing_columns(self, tmp_path):
        """unsafe_filter diagnostics use the documented missingColumns field for omitted subscriber columns."""
        data = validate_public_fixture(tmp_path)
        by_table = {r["table"]: r for r in data["results"]}
        orders_diags = by_table["public.orders"]["diagnostics"]
        assert len(orders_diags) == 1
        assert_diagnostic_contract(
            orders_diags[0],
            "unsafe_filter",
            message_substring="publication filter omits subscriber columns",
            missing_columns=["total_cents"],
        )

    def test_validate_public_fixture_reports_identity_full_filter_blocker(self, tmp_path):
        """filtered REPLICA IDENTITY FULL tables are blocked for human review."""
        data = validate_public_fixture(tmp_path)
        by_table = {r["table"]: r for r in data["results"]}
        audit_diags = by_table["public.audit_log"]["diagnostics"]
        assert len(audit_diags) == 1
        assert_diagnostic_contract(
            audit_diags[0],
            "identity_filter_blocked",
            message_substring="REPLICA IDENTITY FULL",
        )

    def test_validate_runtime_unfiltered_publication_has_empty_published_columns(self, tmp_path):
        """an empty publication column list means the publication sends every publisher column."""
        catalog = tmp_path / "catalog.json"
        catalog.write_text(json.dumps({
            "tables": [
                {"schema": "ops", "name": "widgets", "replicaIdentity": "default", "columns": [
                    {"name": "widget_id", "type": "uuid", "nullable": False, "primaryKey": True},
                    {"name": "owner_id", "type": "uuid", "nullable": False, "primaryKey": False},
                    {"name": "color", "type": "text", "nullable": True, "primaryKey": False}
                ]}
            ],
            "publications": [
                {"name": "all_widget_pub", "tables": [
                    {"schema": "ops", "name": "widgets", "columns": []}
                ]}
            ],
            "subscriptions": [
                {"name": "sub_all_widgets", "publication": "all_widget_pub", "targetTables": [
                    {"schema": "ops", "name": "widgets", "columns": ["widget_id", "owner_id"]}
                ]}
            ]
        }) + "\n")
        out = tmp_path / "validation.json"
        run_cli("validate", "--catalog", str(catalog), "--out", str(out))
        data = json.loads(out.read_text())
        assert data["summary"] == {"subscriptions": 1, "checkedTables": 1, "compatible": 1, "blocked": 0, "diagnostics": 0}
        assert data["results"] == [{
            "subscription": "sub_all_widgets",
            "publication": "all_widget_pub",
            "table": "ops.widgets",
            "status": "compatible",
            "publishedColumns": [],
            "subscriberColumns": ["owner_id", "widget_id"],
            "diagnostics": [],
        }]

    def test_validate_runtime_catalog_summarizes_blocked_edge_rows(self, tmp_path):
        """fresh catalogs keep deterministic schema-qualified rows and blocked summary counts."""
        data = validate_runtime_edge_catalog(tmp_path)
        assert data["summary"] == {"subscriptions": 3, "checkedTables": 3, "compatible": 0, "blocked": 3, "diagnostics": 6}
        assert [(r["subscription"], r["table"], r["publication"]) for r in data["results"]] == [
            ("sub_ghost", "ops.phantoms", "widget_pub"),
            ("sub_missing_pub", "ops.widgets", "missing_pub"),
            ("sub_widgets", "ops.widgets", "widget_pub"),
        ]
        assert all(r["status"] == "blocked" for r in data["results"])

    def test_validate_runtime_catalog_reports_missing_publication(self, tmp_path):
        """missing publications produce a focused blocking object diagnostic."""
        data = validate_runtime_edge_catalog(tmp_path)
        by_sub = {r["subscription"]: r for r in data["results"]}
        assert_diagnostic_contract(
            by_sub["sub_missing_pub"]["diagnostics"][0],
            "missing_publication",
            "not present in the publisher snapshot",
        )

    def test_validate_runtime_catalog_reports_missing_publication_table(self, tmp_path):
        """target tables absent from their referenced publication produce missing_table."""
        data = validate_runtime_edge_catalog(tmp_path)
        by_sub = {r["subscription"]: r for r in data["results"]}
        ghost_codes = [d["code"] for d in by_sub["sub_ghost"]["diagnostics"]]
        assert ghost_codes == ["missing_table", "missing_table"]
        assert_diagnostic_contract(by_sub["sub_ghost"]["diagnostics"][0], "missing_table")

    def test_validate_runtime_catalog_reports_missing_publisher_schema_table(self, tmp_path):
        """target tables absent from the publisher schema also produce a separate missing_table."""
        data = validate_runtime_edge_catalog(tmp_path)
        by_sub = {r["subscription"]: r for r in data["results"]}
        assert_diagnostic_contract(by_sub["sub_ghost"]["diagnostics"][1], "missing_table")
        ghost = by_sub["sub_ghost"]
        assert ghost["publishedColumns"] == []
        assert ghost["subscriberColumns"] == ["id"]

    def test_validate_runtime_catalog_diagnostic_order_for_column_filter_edges(self, tmp_path):
        """column-filter diagnostics are ordered deterministically inside one result."""
        data = validate_runtime_edge_catalog(tmp_path)
        by_sub = {r["subscription"]: r for r in data["results"]}
        widget_diags = by_sub["sub_widgets"]["diagnostics"]
        assert [d["code"] for d in widget_diags] == ["missing_column", "unsafe_filter", "primary_key_omitted"]

    def test_validate_runtime_catalog_reports_missing_columns(self, tmp_path):
        """schema gaps use missing_column with sorted missingColumns."""
        data = validate_runtime_edge_catalog(tmp_path)
        by_sub = {r["subscription"]: r for r in data["results"]}
        widget_diags = by_sub["sub_widgets"]["diagnostics"]
        assert_diagnostic_contract(widget_diags[0], "missing_column", missing_columns=["ghost_col"])

    def test_validate_runtime_catalog_reports_unsafe_filter_columns(self, tmp_path):
        """omitted subscriber columns include schema-missing columns when the filter also omits them."""
        data = validate_runtime_edge_catalog(tmp_path)
        by_sub = {r["subscription"]: r for r in data["results"]}
        widget_diags = by_sub["sub_widgets"]["diagnostics"]
        assert_diagnostic_contract(widget_diags[1], "unsafe_filter", missing_columns=["ghost_col", "widget_id"])

    def test_validate_runtime_catalog_reports_primary_key_omission(self, tmp_path):
        """omitted primary key columns stay separate from subscriber-column filter diagnostics."""
        data = validate_runtime_edge_catalog(tmp_path)
        by_sub = {r["subscription"]: r for r in data["results"]}
        widget_diags = by_sub["sub_widgets"]["diagnostics"]
        assert_diagnostic_contract(
            widget_diags[2],
            "primary_key_omitted",
            message_substring="publication filter omits primary key columns",
            missing_columns=["widget_id"],
        )
