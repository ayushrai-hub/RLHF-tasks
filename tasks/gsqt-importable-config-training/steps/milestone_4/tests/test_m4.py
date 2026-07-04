"""Milestone 4 verifier for recovery schema and dependency reporting."""

from __future__ import annotations

import datetime as dt
import os
import sqlite3
import sys
from pathlib import Path

import pytest


APP_DIR = Path(os.environ.get("APP_DIR", "/app"))


def clear_src_modules() -> None:
    for name in list(sys.modules):
        if name == "src" or name.startswith("src."):
            del sys.modules[name]


def seed_recovery_edges(connection: sqlite3.Connection, now: dt.datetime) -> None:
    connection.execute(
        "UPDATE query_schedule SET completed_at = ? WHERE id = 100",
        ((now - dt.timedelta(minutes=2)).isoformat(timespec="seconds"),),
    )
    connection.executemany(
        """
        INSERT INTO query_schedule
            (id, pod_id, country, human_user_id, scheduled_execution_date,
             deletion_date, priority, locked_at, locked_by_thread, payload_json,
             completed_at, lease_version)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                210,
                3,
                "DE",
                None,
                (now + dt.timedelta(minutes=4)).isoformat(timespec="seconds"),
                None,
                120,
                None,
                None,
                '{"scheduler": {"paused": false}, "tags": ["priority"]}',
                None,
                0,
            ),
            (
                211,
                3,
                "DE",
                None,
                (now + dt.timedelta(minutes=1)).isoformat(timespec="seconds"),
                None,
                130,
                None,
                None,
                "{}",
                None,
                0,
            ),
            (
                212,
                3,
                "DE",
                None,
                (now + dt.timedelta(minutes=1)).isoformat(timespec="seconds"),
                None,
                140,
                None,
                None,
                '{"scheduler": {"paused": true, "reason": "quota"}}',
                None,
                0,
            ),
            (
                300,
                3,
                "DE",
                None,
                (now + dt.timedelta(minutes=2)).isoformat(timespec="seconds"),
                None,
                200,
                None,
                None,
                "{}",
                None,
                0,
            ),
            (
                301,
                3,
                "DE",
                None,
                (now + dt.timedelta(minutes=2)).isoformat(timespec="seconds"),
                None,
                199,
                None,
                None,
                "{}",
                None,
                0,
            ),
        ],
    )
    connection.executemany(
        "INSERT INTO query_dependencies (query_id, depends_on_id) VALUES (?, ?)",
        [(210, 100), (211, 150), (300, 301), (301, 300)],
    )
    connection.commit()


class TestMilestone4:
    def test_recovery_report_migrates_and_explains_claimability(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Recovery report combines migration, dependency, pause, cycle, and stale checks."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        monkeypatch.delenv("GSQT_QUERY_DSN", raising=False)
        clear_src_modules()

        from src.query_scheduling.recovery import build_recovery_report, ensure_recovery_schema
        from src.testing.fakes import build_memory_query_db

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        connection = build_memory_query_db(now=now)
        ensure_recovery_schema(connection)
        seed_recovery_edges(connection, now)

        report = build_recovery_report(connection, now=now)

        assert report["schema"] == {
            "payload_supported": True,
            "completed_supported": True,
            "lease_supported": True,
            "dependencies_supported": True,
        }
        assert report["ready_by_country"] == {"DE": [210, 101], "FR": [150]}
        assert report["blocked_by_dependency"] == {
            "211": [150],
            "300": [301],
            "301": [300],
        }
        assert report["cycle_ids"] == [300, 301]
        assert report["paused_ids"] == [212]
        assert report["stale_lock_ids"] == [150]

    def test_recovery_schema_is_idempotent_on_sparse_legacy_database(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Recovery migration preserves sparse legacy data and can be run repeatedly."""
        monkeypatch.syspath_prepend(str(APP_DIR))
        clear_src_modules()

        from src.query_scheduling.recovery import build_recovery_report, ensure_recovery_schema

        now = dt.datetime(2026, 1, 1, 12, 0, 0)
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.executescript(
            """
            CREATE TABLE query_schedule (
                id INTEGER PRIMARY KEY,
                pod_id INTEGER NOT NULL,
                country TEXT NOT NULL,
                human_user_id INTEGER,
                scheduled_execution_date TEXT NOT NULL,
                deletion_date TEXT,
                priority INTEGER NOT NULL DEFAULT 0,
                locked_at TEXT
            );
            INSERT INTO query_schedule
                (id, pod_id, country, human_user_id, scheduled_execution_date,
                 deletion_date, priority, locked_at)
            VALUES (7, 3, 'DE', NULL, '2026-01-01 12:05:00', NULL, 5, NULL);
            """
        )

        ensure_recovery_schema(connection)
        ensure_recovery_schema(connection)
        report = build_recovery_report(connection, now=now)
        row = connection.execute(
            """
            SELECT payload_json, completed_at, lease_version
            FROM query_schedule
            WHERE id = 7
            """
        ).fetchone()

        assert dict(row) == {"payload_json": "{}", "completed_at": None, "lease_version": 0}
        assert report["ready_by_country"] == {"DE": [7]}
        assert report["blocked_by_dependency"] == {}
        assert report["cycle_ids"] == []
        assert report["paused_ids"] == []
        assert report["stale_lock_ids"] == []
