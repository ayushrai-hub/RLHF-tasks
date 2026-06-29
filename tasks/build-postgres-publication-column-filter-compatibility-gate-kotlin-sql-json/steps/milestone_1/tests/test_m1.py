"""Verifier for catalog snapshot parsing."""

import json
import sqlite3
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


class TestMilestone1:
    def test_parse_public_fixture_writes_full_catalog_and_sqlite(self, tmp_path):
        """parse keeps publication filters, subscriptions, identity metadata, and inspectable SQLite rows."""
        db = tmp_path / "nested" / "catalog.db"
        out = tmp_path / "nested" / "catalog.json"
        run_cli(
            "parse",
            "--schema", "/app/input/publisher_schema.sql",
            "--publications", "/app/input/publications.sql",
            "--subscriptions", "/app/input/subscriptions.json",
            "--db", str(db),
            "--out", str(out),
        )
        text = out.read_text()
        assert text.endswith("\n")
        assert text.startswith("{\n")
        assert "\n  \"tables\"" in text
        data = json.loads(text)
        assert list(data.keys()) == ["tables", "publications", "subscriptions"]
        assert [t["name"] for t in data["tables"]] == ["accounts", "audit_log", "orders"]
        accounts = next(t for t in data["tables"] if t["name"] == "accounts")
        acct_cols = {c["name"]: c for c in accounts["columns"]}
        assert acct_cols["id"] == {"name": "id", "type": "bigint", "nullable": False, "primaryKey": True}
        assert acct_cols["email"] == {"name": "email", "type": "text", "nullable": False, "primaryKey": False}
        audit = next(t for t in data["tables"] if t["name"] == "audit_log")
        assert audit["replicaIdentity"] == "full"
        app_pub = next(p for p in data["publications"] if p["name"] == "app_pub")
        assert app_pub["tables"][0] == {"schema": "public", "name": "accounts", "columns": ["id", "email", "status"]}
        assert data["subscriptions"][0]["name"] == "sub_app"
        conn = sqlite3.connect(db)
        rows = conn.execute(
            "SELECT publication_name, schema_name, table_name, columns_json FROM publication_tables ORDER BY 1,2,3"
        ).fetchall()
        assert rows == [
            ("app_pub", "public", "accounts", '["id","email","status"]'),
            ("app_pub", "public", "orders", '["id","account_id","state"]'),
            ("audit_pub", "public", "audit_log", '["id","actor_id","action"]'),
        ]
        table_rows = conn.execute(
            "SELECT schema_name, table_name, replica_identity FROM tables ORDER BY 1,2"
        ).fetchall()
        assert table_rows == [
            ("public", "accounts", "default"),
            ("public", "audit_log", "full"),
            ("public", "orders", "default"),
        ]
        col_rows = conn.execute(
            "SELECT table_name, column_name, data_type, nullable, primary_key FROM columns "
            "WHERE table_name='accounts' ORDER BY column_name"
        ).fetchall()
        assert ("accounts", "email", "text", 0, 0) in col_rows
        assert ("accounts", "id", "bigint", 0, 1) in col_rows
        pub_rows = conn.execute("SELECT publication_name FROM publications ORDER BY 1").fetchall()
        assert pub_rows == [("app_pub",), ("audit_pub",)]
        sub_rows = conn.execute("SELECT subscription_name, publication_name FROM subscriptions ORDER BY 1").fetchall()
        assert sub_rows == [("sub_app", "app_pub"), ("sub_audit", "audit_pub")]
        sub_table_rows = conn.execute(
            "SELECT subscription_name, schema_name, table_name, columns_json FROM subscription_tables ORDER BY 1,2,3"
        ).fetchall()
        assert sub_table_rows == [
            ("sub_app", "public", "accounts", '["id","email","status"]'),
            ("sub_app", "public", "orders", '["id","account_id","total_cents","state"]'),
            ("sub_audit", "public", "audit_log", '["id","actor_id","action"]'),
        ]

    def test_parse_runtime_sql_with_empty_publication_and_alter_add_table(self, tmp_path):
        """parse handles fresh SQL with an empty publication and ALTER PUBLICATION ADD TABLE column lists."""
        schema = tmp_path / "schema.sql"
        pubs = tmp_path / "publications.sql"
        subs = tmp_path / "subs.json"
        db = tmp_path / "db" / "runtime.sqlite"
        out = tmp_path / "out" / "runtime.json"
        schema.write_text(
            """
            CREATE TABLE ops.widgets (
              widget_id uuid PRIMARY KEY,
              owner_id uuid NOT NULL,
              color text,
              score numeric(12,2) NOT NULL
            );
            CREATE TABLE ops.events (
              event_id bigint PRIMARY KEY,
              widget_id uuid NOT NULL,
              payload jsonb
            );
            ALTER TABLE ops.events REPLICA IDENTITY FULL;
            """
        )
        pubs.write_text(
            """
            CREATE PUBLICATION empty_pub;
            CREATE PUBLICATION widget_pub FOR TABLE ops.widgets (widget_id, owner_id);
            ALTER PUBLICATION widget_pub ADD TABLE ops.events (event_id, widget_id);
            """
        )
        subs.write_text(json.dumps({
            "subscriptions": [
                {"name": "sub_widgets", "publication": "widget_pub", "tables": [
                    {"schema": "ops", "name": "widgets", "columns": ["widget_id", "owner_id"]},
                    {"schema": "ops", "name": "events", "columns": ["event_id", "widget_id"]}
                ]}
            ]
        }))
        run_cli("parse", "--schema", str(schema), "--publications", str(pubs), "--subscriptions", str(subs), "--db", str(db), "--out", str(out))
        data = json.loads(out.read_text())
        assert [p["name"] for p in data["publications"]] == ["empty_pub", "widget_pub"]
        assert data["publications"][0]["tables"] == []
        widgets = next(t for t in data["tables"] if t["name"] == "widgets")
        assert [c["name"] for c in widgets["columns"]] == ["color", "owner_id", "score", "widget_id"]
        widget_cols = {c["name"]: c for c in widgets["columns"]}
        assert widget_cols["color"]["nullable"] is True
        assert widget_cols["owner_id"]["nullable"] is False
        events = next(t for t in data["publications"][1]["tables"] if t["name"] == "events")
        assert events["columns"] == ["event_id", "widget_id"]
        assert data["subscriptions"][0]["targetTables"] == [
            {"schema": "ops", "name": "events", "columns": ["event_id", "widget_id"]},
            {"schema": "ops", "name": "widgets", "columns": ["widget_id", "owner_id"]},
        ]

    def test_parse_runtime_table_level_primary_key_and_type_modifiers(self, tmp_path):
        """parse handles table-level primary keys and data types containing commas."""
        schema = tmp_path / "schema.sql"
        pubs = tmp_path / "publications.sql"
        subs = tmp_path / "subs.json"
        db = tmp_path / "db.sqlite"
        out = tmp_path / "catalog.json"
        schema.write_text(
            """
            CREATE TABLE billing.invoice_lines (
              invoice_id bigint NOT NULL,
              line_no integer NOT NULL,
              amount numeric(12,2) NOT NULL,
              note text,
              PRIMARY KEY (invoice_id, line_no)
            );
            """
        )
        pubs.write_text("CREATE PUBLICATION billing_pub FOR TABLE billing.invoice_lines (invoice_id, line_no, amount);")
        subs.write_text(json.dumps({
            "subscriptions": [
                {"name": "sub_billing", "publication": "billing_pub", "tables": [
                    {"schema": "billing", "name": "invoice_lines", "columns": ["invoice_id", "line_no", "amount"]}
                ]}
            ]
        }))
        run_cli("parse", "--schema", str(schema), "--publications", str(pubs), "--subscriptions", str(subs), "--db", str(db), "--out", str(out))
        data = json.loads(out.read_text())
        cols = {c["name"]: c for c in data["tables"][0]["columns"]}
        assert cols["invoice_id"]["primaryKey"] is True
        assert cols["line_no"]["primaryKey"] is True
        assert cols["amount"]["type"] == "numeric(12,2)"
        assert cols["amount"]["nullable"] is False
