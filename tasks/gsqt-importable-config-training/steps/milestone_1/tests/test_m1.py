"""Milestone 1 verifier for import-safe database configuration."""

from __future__ import annotations

import importlib
import os
import sqlite3
import sys
from pathlib import Path

import pytest


APP_DIR = Path(os.environ.get("APP_DIR", "/app"))
MODULES = [
    "src.config.database",
    "src.query_scheduling.scheduler",
    "src.steps.generator",
    "src.user_service",
    "src.node_service",
]


def clear_src_modules() -> None:
    for name in list(sys.modules):
        if name == "src" or name.startswith("src."):
            del sys.modules[name]


class TestMilestone1:
    def test_core_modules_import_without_database_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Core service modules import without production database DSNs."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        monkeypatch.delenv("GSQT_NODE_DSN", raising=False)
        clear_src_modules()

        for module_name in MODULES:
            module = importlib.import_module(module_name)
            assert module is not None

    def test_database_accessors_fail_clearly_when_unconfigured(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Lazy database accessors name the missing DSN when called unconfigured."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        monkeypatch.delenv("GSQT_NODE_DSN", raising=False)
        clear_src_modules()

        database = importlib.import_module("src.config.database")

        with pytest.raises(RuntimeError, match="GSQT_QUERY_DSN"):
            database.get_query_engine()

        with pytest.raises(RuntimeError, match="GSQT_NODE_DSN"):
            database.get_node_engine()

    def test_database_accessors_open_configured_sqlite_connections(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Lazy accessors still open usable SQLite connections when configured."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.setenv("GSQT_QUERY_DSN", str(tmp_path / "query.sqlite"))
        monkeypatch.setenv("GSQT_NODE_DSN", str(tmp_path / "node.sqlite"))
        clear_src_modules()

        database = importlib.import_module("src.config.database")

        query_engine = database.get_query_engine()
        node_engine = database.get_node_engine()

        assert isinstance(query_engine, sqlite3.Connection)
        assert isinstance(node_engine, sqlite3.Connection)
        query_engine.execute("CREATE TABLE query_probe (id INTEGER PRIMARY KEY)")
        node_engine.execute("CREATE TABLE node_probe (id INTEGER PRIMARY KEY)")

    def test_database_accessors_follow_changed_dsn_values(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Accessors reopen connections when their configured DSN changes."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        first_path = tmp_path / "first.sqlite"
        second_path = tmp_path / "second.sqlite"
        first_node_path = tmp_path / "first-node.sqlite"
        second_node_path = tmp_path / "second-node.sqlite"
        monkeypatch.setenv("GSQT_QUERY_DSN", str(first_path))
        monkeypatch.setenv("GSQT_NODE_DSN", str(first_node_path))
        clear_src_modules()

        database = importlib.import_module("src.config.database")
        first = database.get_query_engine()
        first.execute("CREATE TABLE marker (value TEXT)")
        first.execute("INSERT INTO marker VALUES ('first')")
        first.commit()
        first_node = database.get_node_engine()
        first_node.execute("CREATE TABLE marker (value TEXT)")
        first_node.execute("INSERT INTO marker VALUES ('first-node')")
        first_node.commit()

        second_seed = sqlite3.connect(second_path)
        second_seed.execute("CREATE TABLE marker (value TEXT)")
        second_seed.execute("INSERT INTO marker VALUES ('second')")
        second_seed.commit()
        second_seed.close()
        second_node_seed = sqlite3.connect(second_node_path)
        second_node_seed.execute("CREATE TABLE marker (value TEXT)")
        second_node_seed.execute("INSERT INTO marker VALUES ('second-node')")
        second_node_seed.commit()
        second_node_seed.close()

        monkeypatch.setenv("GSQT_QUERY_DSN", str(second_path))
        monkeypatch.setenv("GSQT_NODE_DSN", str(second_node_path))
        second = database.get_query_engine()
        second_node = database.get_node_engine()

        assert second is not first
        assert second.execute("SELECT value FROM marker").fetchone()[0] == "second"
        assert second_node is not first_node
        assert second_node.execute("SELECT value FROM marker").fetchone()[0] == "second-node"

    def test_database_accessors_support_sqlite_uri_dsns(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """SQLite file: URI DSNs are opened as URIs, including mode=rw."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        db_path = tmp_path / "query.sqlite"
        seed = sqlite3.connect(db_path)
        seed.execute("CREATE TABLE marker (value TEXT)")
        seed.execute("INSERT INTO marker VALUES ('uri')")
        seed.commit()
        seed.close()

        monkeypatch.setenv("GSQT_QUERY_DSN", f"file:{db_path.as_posix()}?mode=rw")
        monkeypatch.setenv("GSQT_NODE_DSN", str(tmp_path / "node.sqlite"))
        clear_src_modules()

        database = importlib.import_module("src.config.database")

        query_engine = database.get_query_engine()
        assert query_engine.execute("SELECT value FROM marker").fetchone()[0] == "uri"

    def test_update_by_id_still_updates_an_explicit_connection(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """DatabaseOperations.update_by_id works with an explicit SQLite connection."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        clear_src_modules()
        database = importlib.import_module("src.config.database")

        db_path = tmp_path / "query.sqlite"
        connection = sqlite3.connect(db_path)
        connection.execute("CREATE TABLE query_schedule (id INTEGER PRIMARY KEY, human_user_id INTEGER)")
        connection.execute("INSERT INTO query_schedule (id, human_user_id) VALUES (7, 11)")
        connection.commit()

        database.DatabaseOperations.update_by_id(
            connection, "query_schedule", 7, human_user_id=None
        )

        value = connection.execute(
            "SELECT human_user_id FROM query_schedule WHERE id = 7"
        ).fetchone()[0]
        assert value is None
