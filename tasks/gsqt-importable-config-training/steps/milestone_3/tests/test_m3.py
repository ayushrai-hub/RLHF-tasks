"""Milestone 3 verifier for fake-backed dry-run healthcheck."""

from __future__ import annotations

import datetime as dt
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


APP_DIR = Path(os.environ.get("APP_DIR", "/app"))


def unload_healthcheck() -> None:
    sys.modules.pop("src.devtools.healthcheck", None)


class RaceOnceCursor:
    """Applies one competing lock after the scheduler reads query 100."""

    def __init__(self, cursor, connection: "RaceOnceConnection"):
        self._cursor = cursor
        self._connection = connection

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is not None and not self._connection.race_applied and row["id"] == 100:
            self._connection.race_applied = True
            self._connection.base.execute(
                """
                UPDATE query_schedule
                SET human_user_id = ?, locked_at = ?, locked_by_thread = ?
                WHERE id = 100
                """,
                (
                    99,
                    self._connection.race_time.isoformat(timespec="seconds"),
                    77,
                ),
            )
            self._connection.base.commit()
        return row

    def __getattr__(self, name: str):
        return getattr(self._cursor, name)


class RaceOnceConnection:
    """Proxy that races the first ordered query_schedule selection."""

    def __init__(self, base, race_time: dt.datetime):
        self.base = base
        self.race_time = race_time
        self.race_applied = False

    def execute(self, sql: str, parameters=(), /):
        cursor = self.base.execute(sql, parameters)
        normalized = " ".join(sql.upper().split())
        if (
            normalized.startswith("SELECT")
            and " FROM QUERY_SCHEDULE " in f" {normalized} "
            and " ORDER BY " in f" {normalized} "
        ):
            return RaceOnceCursor(cursor, self)
        return cursor

    def commit(self) -> None:
        self.base.commit()

    def __getattr__(self, name: str):
        return getattr(self.base, name)


class TestMilestone3:
    def test_fake_databases_drive_injected_services_without_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Seeded fake databases drive the injected services without DSN variables."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        monkeypatch.delenv("GSQT_NODE_DSN", raising=False)

        from src.node_service import NodeService
        from src.query_scheduling.scheduler import QueryScheduler
        from src.steps.generator import StepBuilder
        from src.testing.fakes import build_memory_node_db, build_memory_query_db
        from src.user_service import UserService

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        query_db = build_memory_query_db(now=now)
        node_db = build_memory_node_db()

        scheduler = QueryScheduler(query_engine=query_db)
        selected, camo = scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=21
        )
        steps = StepBuilder(query_engine=query_db).build_query_steps(selected)

        assert camo is False
        assert selected["id"] == 100
        assert [step["type"] for step in steps] == ["google_search", "click_result"]

        stale, stale_camo = scheduler.get_and_lock_query(
            "FR", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=22
        )
        assert stale_camo is False
        assert stale["id"] == 150
        assert tuple(
            query_db.execute(
                "SELECT human_user_id, locked_at FROM query_schedule WHERE id = 151"
            ).fetchone()
        ) == (78, (now - dt.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"))

        scheduler.unlock_query(100)
        UserService(query_engine=query_db).unlock_user(42)
        online_nodes, user_pool = NodeService(node_engine=node_db).get_online_nodes_and_user_pool()
        raw_online_rows = node_db.execute(
            """
            SELECT nhu.human_user_id, n.uuid
            FROM nodes_to_human_users AS nhu
            INNER JOIN nodes AS n ON nhu.node_uuid = n.uuid
            WHERE n.currently_online = 'TRUE'
            """
        ).fetchall()
        lock_events = [
            dict(row)
            for row in query_db.execute(
                """
                SELECT query_schedule_id, human_user_id, thread_id, action, event_time,
                       previous_human_user_id, previous_locked_at
                FROM query_lock_events
                ORDER BY id
                """
            )
        ]

        assert query_db.execute(
            "SELECT human_user_id FROM query_schedule WHERE id = 100"
        ).fetchone()[0] is None
        assert query_db.execute(
            "SELECT last_locked FROM human_users WHERE id = 42"
        ).fetchone()[0] is None
        assert lock_events[:2] == [
            {
                "query_schedule_id": 100,
                "human_user_id": 42,
                "thread_id": 21,
                "action": "claim",
                "event_time": now.isoformat(timespec="seconds"),
                "previous_human_user_id": None,
                "previous_locked_at": None,
            },
            {
                "query_schedule_id": 150,
                "human_user_id": 42,
                "thread_id": 22,
                "action": "reclaim",
                "event_time": now.isoformat(timespec="seconds"),
                "previous_human_user_id": 77,
                "previous_locked_at": (now - dt.timedelta(minutes=45)).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            },
        ]
        assert lock_events[2]["query_schedule_id"] == 100
        assert lock_events[2]["human_user_id"] is None
        assert lock_events[2]["thread_id"] is None
        assert lock_events[2]["action"] == "unlock"
        assert dt.datetime.fromisoformat(lock_events[2]["event_time"])
        assert lock_events[2]["previous_human_user_id"] is None
        assert lock_events[2]["previous_locked_at"] is None
        assert len(raw_online_rows) > len(user_pool)
        assert len(online_nodes) == 1
        assert online_nodes == [{"uuid": "node-a", "currently_online": "TRUE"}]
        assert [row["human_user_id"] for row in user_pool] == [42, 44]

        legacy_db = build_memory_query_db(now=now, legacy=True)
        legacy_scheduler = QueryScheduler(query_engine=legacy_db)
        legacy_selected, legacy_camo = legacy_scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=31
        )
        legacy_steps = StepBuilder(query_engine=legacy_db).build_query_steps(legacy_selected)
        legacy_stale, legacy_stale_camo = legacy_scheduler.get_and_lock_query(
            "FR", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=32
        )
        legacy_scheduler.unlock_query(100)
        legacy_event_actions = [
            row["action"]
            for row in legacy_db.execute("SELECT action FROM query_lock_events ORDER BY id")
        ]

        legacy_columns = {
            row["name"] for row in legacy_db.execute("PRAGMA table_info(query_schedule)")
        }
        assert "locked_by_thread" not in legacy_columns
        assert legacy_camo is False
        assert legacy_selected["id"] == 100
        assert [step["type"] for step in legacy_steps] == ["google_search", "click_result"]
        assert legacy_stale_camo is False
        assert legacy_stale["id"] == 150
        assert tuple(
            legacy_db.execute(
                "SELECT human_user_id, locked_at FROM query_schedule WHERE id = 151"
            ).fetchone()
        ) == (78, (now - dt.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"))
        assert tuple(
            legacy_db.execute(
                "SELECT human_user_id, locked_at FROM query_schedule WHERE id = 100"
            ).fetchone()
        ) == (None, None)
        assert legacy_event_actions == ["claim", "reclaim", "unlock"]

    def test_fake_query_priority_order_is_not_id_or_date_order(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A higher-priority fake row wins even with a later schedule and higher id."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)

        from src.query_scheduling.scheduler import QueryScheduler
        from src.testing.fakes import build_memory_query_db

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        query_db = build_memory_query_db(now=now)
        query_db.execute(
            """
            INSERT INTO query_schedule
                (id, pod_id, country, human_user_id, scheduled_execution_date,
                 deletion_date, priority, locked_at, locked_by_thread)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                102,
                3,
                "DE",
                None,
                (now + dt.timedelta(minutes=3)).isoformat(timespec="seconds"),
                None,
                95,
                None,
                None,
            ),
        )
        query_db.commit()

        selected, camo = QueryScheduler(query_engine=query_db).get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=25
        )

        assert camo is False
        assert selected["id"] == 102

    def test_fake_database_retry_and_optional_audit_table_paths(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Fake query DBs prove race retry and tolerate missing audit tables."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)

        from src.query_scheduling.scheduler import QueryScheduler
        from src.testing.fakes import build_memory_query_db

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        query_db = build_memory_query_db(now=now)
        race_connection = RaceOnceConnection(query_db, now + dt.timedelta(seconds=1))
        scheduler = QueryScheduler(query_engine=race_connection)

        selected, camo = scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=50
        )

        assert race_connection.race_applied is True
        assert camo is False
        assert selected["id"] == 101
        assert tuple(
            query_db.execute(
                "SELECT human_user_id, locked_at, locked_by_thread FROM query_schedule WHERE id = 100"
            ).fetchone()
        ) == (99, (now + dt.timedelta(seconds=1)).isoformat(timespec="seconds"), 77)
        assert tuple(
            query_db.execute(
                "SELECT human_user_id, locked_at, locked_by_thread FROM query_schedule WHERE id = 101"
            ).fetchone()
        ) == (42, now.isoformat(timespec="seconds"), 50)
        race_events = [
            dict(row)
            for row in query_db.execute(
                """
                SELECT query_schedule_id, human_user_id, thread_id, action, event_time,
                       previous_human_user_id, previous_locked_at
                FROM query_lock_events
                ORDER BY id
                """
            )
        ]
        assert race_events == [
            {
                "query_schedule_id": 100,
                "human_user_id": 42,
                "thread_id": 50,
                "action": "race_miss",
                "event_time": now.isoformat(timespec="seconds"),
                "previous_human_user_id": None,
                "previous_locked_at": None,
            },
            {
                "query_schedule_id": 101,
                "human_user_id": 42,
                "thread_id": 50,
                "action": "claim",
                "event_time": now.isoformat(timespec="seconds"),
                "previous_human_user_id": None,
                "previous_locked_at": None,
            },
        ]

        no_audit_db = build_memory_query_db(now=now)
        no_audit_db.execute("DROP TABLE query_lock_events")
        no_audit_db.commit()
        no_audit_scheduler = QueryScheduler(query_engine=no_audit_db)
        no_audit_selected, no_audit_camo = no_audit_scheduler.get_and_lock_query(
            "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=60
        )
        no_audit_scheduler.unlock_query(no_audit_selected["id"])

        assert no_audit_camo is False
        assert no_audit_selected["id"] == 100
        assert no_audit_db.execute(
            "SELECT human_user_id FROM query_schedule WHERE id = 100"
        ).fetchone()[0] is None

    def test_healthcheck_uses_fake_database_data_dynamically(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """run_healthcheck reflects fake DB contents rather than hardcoded JSON."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        monkeypatch.delenv("GSQT_NODE_DSN", raising=False)

        from src.testing import fakes

        unload_healthcheck()
        healthcheck = importlib.import_module("src.devtools.healthcheck")
        original_builder = fakes.build_memory_query_db

        def build_variant_query_db(now: dt.datetime | None = None, legacy: bool = False):
            connection = original_builder(now=now, legacy=legacy)
            connection.execute("UPDATE query_schedule SET id = 321 WHERE id = 100")
            connection.execute(
                "UPDATE query_schedule_steps SET query_schedule_id = 321 WHERE query_schedule_id = 100"
            )
            connection.execute("DELETE FROM query_schedule WHERE id = 150")
            connection.commit()
            return connection

        monkeypatch.setattr(fakes, "build_memory_query_db", build_variant_query_db)
        report = healthcheck.run_healthcheck()

        assert report["selected_query_id"] == 321
        assert report["loaded_step_types"] == ["google_search", "click_result"]
        assert report["camo_query"] is False
        assert report["stale_query_claimed"] is False
        assert report["lock_event_actions"] == ["claim", "unlock"]
        assert report["schema_reports"]["modern"]["selected_query_id"] == 321
        assert report["schema_reports"]["modern"]["lock_event_actions"] == [
            "claim",
            "unlock",
        ]
        assert report["schema_reports"]["legacy"]["selected_query_id"] == 321
        assert report["schema_reports"]["legacy"]["stale_query_claimed"] is False
        assert report["schema_reports"]["legacy"]["lock_event_actions"] == [
            "claim",
            "unlock",
        ]
        assert report["retry_report"] == {
            "race_applied": True,
            "raced_query_id": 321,
            "selected_query_id": 101,
            "camo_query": False,
            "lock_event_actions": ["race_miss", "claim"],
        }
        assert report["auditless_report"] == {
            "selected_query_id": 321,
            "camo_query": False,
            "query_unlocked": True,
            "lock_event_actions": [],
        }

    def test_healthcheck_json_runs_without_production_configuration(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The healthcheck CLI emits stable JSON without production configuration."""
        env = os.environ.copy()
        env["PYTHONPATH"] = str(APP_DIR)
        env.pop("GSQT_QUERY_DSN", None)
        env.pop("GSQT_NODE_DSN", None)

        completed = subprocess.run(
            [sys.executable, "-m", "src.devtools.healthcheck", "--json"],
            cwd=APP_DIR,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )

        report = json.loads(completed.stdout)
        assert report["imported"] is True
        assert report["selected_query_id"] == 100
        assert report["camo_query"] is False
        assert report["loaded_step_types"] == ["google_search", "click_result"]
        assert report["query_unlocked"] is True
        assert report["user_unlocked"] is True
        assert report["online_node_count"] == 1
        assert report["stale_query_claimed"] is True
        assert report["node_user_count"] == 2
        assert report["lock_event_actions"] == ["claim", "reclaim", "unlock"]
        assert report["retry_report"] == {
            "race_applied": True,
            "raced_query_id": 100,
            "selected_query_id": 101,
            "camo_query": False,
            "lock_event_actions": ["race_miss", "claim"],
        }
        assert report["auditless_report"] == {
            "selected_query_id": 100,
            "camo_query": False,
            "query_unlocked": True,
            "lock_event_actions": [],
        }
        assert report["schema_reports"]["modern"]["locked_by_thread_supported"] is True
        assert report["schema_reports"]["legacy"]["locked_by_thread_supported"] is False
        assert report["schema_reports"]["legacy"]["selected_query_id"] == 100
        assert report["schema_reports"]["legacy"]["loaded_step_types"] == [
            "google_search",
            "click_result",
        ]
        assert report["schema_reports"]["legacy"]["stale_query_claimed"] is True
        assert report["schema_reports"]["legacy"]["lock_event_actions"] == [
            "claim",
            "reclaim",
            "unlock",
        ]
        assert completed.stderr == ""
