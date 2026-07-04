"""Seed data for recovery replay diagnostics."""

from __future__ import annotations

import datetime as dt
import sqlite3

from src.query_scheduling.recovery import ensure_recovery_schema
from src.testing.fakes import build_memory_query_db


def build_recovery_query_db(now: dt.datetime | None = None) -> sqlite3.Connection:
    current_time = now or dt.datetime(2026, 1, 1, 12, 0, 0)
    connection = build_memory_query_db(now=current_time)
    ensure_recovery_schema(connection)
    connection.execute(
        "UPDATE query_schedule SET completed_at = ? WHERE id = 100",
        ((current_time - dt.timedelta(minutes=2)).isoformat(timespec="seconds"),),
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
                (current_time + dt.timedelta(minutes=4)).isoformat(timespec="seconds"),
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
                (current_time + dt.timedelta(minutes=1)).isoformat(timespec="seconds"),
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
                (current_time + dt.timedelta(minutes=1)).isoformat(timespec="seconds"),
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
                (current_time + dt.timedelta(minutes=2)).isoformat(timespec="seconds"),
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
                (current_time + dt.timedelta(minutes=2)).isoformat(timespec="seconds"),
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
    return connection
