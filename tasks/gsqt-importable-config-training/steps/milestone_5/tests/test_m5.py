"""Milestone 5 verifier for recovery replay diagnostics."""

from __future__ import annotations

import ast
import datetime as dt
import importlib
import inspect
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest


APP_DIR = Path(os.environ.get("APP_DIR", "/app"))


class TestMilestone5:
    def test_recovery_replay_claims_dynamic_scenario_without_hardcoding(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Monkeypatched recovery scenarios flow through report, claim, and audit logic."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        monkeypatch.delenv("GSQT_NODE_DSN", raising=False)

        from src.testing import recovery_scenarios

        replay_mod = importlib.import_module("src.devtools.recovery_replay")
        replay_source = inspect.getsource(replay_mod)
        replay_tree = ast.parse(replay_source)
        imported_healthcheck = False
        for node in ast.walk(replay_tree):
            if isinstance(node, ast.Import):
                imported_healthcheck = any(
                    alias.name in {"healthcheck", "src.devtools.healthcheck"}
                    or alias.name.startswith("src.devtools.healthcheck.")
                    or alias.name.startswith("devtools.healthcheck")
                    for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imported_healthcheck = (
                    module in {"healthcheck", "src.devtools.healthcheck"}
                    or module.startswith("src.devtools.healthcheck.")
                    or module.startswith("devtools.healthcheck")
                    or (
                        module in {"src.devtools", "devtools", ""}
                        and any(alias.name == "healthcheck" for alias in node.names)
                    )
                )
            if imported_healthcheck:
                break
        assert imported_healthcheck is False
        original_builder = recovery_scenarios.build_recovery_query_db

        def build_variant(now: dt.datetime | None = None):
            connection = original_builder(now=now)
            connection.execute("UPDATE query_schedule SET id = 260 WHERE id = 210")
            connection.execute(
                "UPDATE query_dependencies SET query_id = 260 WHERE query_id = 210"
            )
            connection.execute("UPDATE query_schedule SET id = 280 WHERE id = 150")
            connection.execute(
                "UPDATE query_dependencies SET depends_on_id = 280 WHERE depends_on_id = 150"
            )
            connection.commit()
            return connection

        monkeypatch.setattr(recovery_scenarios, "build_recovery_query_db", build_variant)

        report = replay_mod.run_recovery_replay()

        assert report["initial_ready"] == {"DE": [260, 101], "FR": [280]}
        assert report["initial_blocked"] == {
            "211": [280],
            "300": [301],
            "301": [300],
        }
        assert report["initial_cycles"] == [300, 301]
        assert report["initial_paused"] == [212]
        assert report["claimed_ids"] == [260, 280]
        assert report["camo_flags"] == [False, False]
        assert report["final_ready"] == {"DE": [101]}
        assert report["final_stale_locks"] == []
        assert report["event_metadata"] == [
            {"source": "recovery_replay", "ready_before": [260, 101]},
            {"source": "recovery_replay", "ready_before": [280]},
        ]

    def test_file_backed_recovery_claims_do_not_double_claim(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Two file-backed connections claim distinct ready rows with lease increments."""
        monkeypatch.syspath_prepend(str(APP_DIR))

        from src.devtools.recovery_replay import claim_next_ready
        from src.testing.recovery_scenarios import build_recovery_query_db

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        source = build_recovery_query_db(now=now)
        db_path = tmp_path / "recovery.sqlite"
        target = sqlite3.connect(db_path)
        source.backup(target)
        target.close()
        first_connection = sqlite3.connect(db_path, timeout=5.0)
        first_connection.row_factory = sqlite3.Row
        second_connection = sqlite3.connect(db_path, timeout=5.0)
        second_connection.row_factory = sqlite3.Row

        try:
            first, first_camo = claim_next_ready(
                first_connection,
                "DE",
                {"human_user_id": 42, "pod_id": 3},
                now=now,
                thread_id=501,
            )
            second, second_camo = claim_next_ready(
                second_connection,
                "DE",
                {"human_user_id": 43, "pod_id": 3},
                now=now,
                thread_id=502,
            )
            rows = [
                dict(row)
                for row in first_connection.execute(
                    """
                    SELECT id, human_user_id, locked_by_thread, lease_version
                    FROM query_schedule
                    WHERE id IN (101, 210)
                    ORDER BY id
                    """
                )
            ]
        finally:
            first_connection.close()
            second_connection.close()

        assert first_camo is False
        assert second_camo is False
        assert [first["id"], second["id"]] == [210, 101]
        assert rows == [
            {"id": 101, "human_user_id": 43, "locked_by_thread": 502, "lease_version": 1},
            {"id": 210, "human_user_id": 42, "locked_by_thread": 501, "lease_version": 1},
        ]

    def test_recovery_replay_json_cli_is_stable_without_production_configuration(
        self,
    ) -> None:
        """Recovery replay CLI emits only JSON and avoids production DSN variables."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(APP_DIR)
        env.pop("GSQT_QUERY_DSN", None)
        env.pop("GSQT_NODE_DSN", None)

        completed = subprocess.run(
            [sys.executable, "-m", "src.devtools.recovery_replay", "--json"],
            cwd=APP_DIR,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )

        report = json.loads(completed.stdout)
        assert report["initial_ready"] == {"DE": [210, 101], "FR": [150]}
        assert report["initial_blocked"] == {
            "211": [150],
            "300": [301],
            "301": [300],
        }
        assert report["claimed_ids"] == [210, 150]
        assert report["camo_flags"] == [False, False]
        assert report["final_ready"] == {"DE": [101]}
        assert report["event_metadata"] == [
            {"source": "recovery_replay", "ready_before": [210, 101]},
            {"source": "recovery_replay", "ready_before": [150]},
        ]
        assert completed.stderr == ""
