"""Deterministic fake databases for local GSQT service checks."""

from __future__ import annotations

import datetime as dt
import sqlite3


def build_memory_query_db(
    now: dt.datetime | None = None, legacy: bool = False
) -> sqlite3.Connection:
    current_time = now or dt.datetime(2026, 1, 1, 12, 0, 0)
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    locked_by_thread_column = "" if legacy else ", locked_by_thread INTEGER"
    position_column = "" if legacy else ", position INTEGER"
    connection.executescript(
        f"""
        CREATE TABLE query_schedule (
            id INTEGER PRIMARY KEY,
            pod_id INTEGER NOT NULL,
            country TEXT NOT NULL,
            human_user_id INTEGER,
            scheduled_execution_date TEXT NOT NULL,
            deletion_date TEXT,
            priority INTEGER NOT NULL DEFAULT 0,
            locked_at TEXT{locked_by_thread_column}
        );
        CREATE TABLE query_schedule_steps (
            id INTEGER PRIMARY KEY,
            query_schedule_id INTEGER NOT NULL{position_column},
            type TEXT NOT NULL,
            value TEXT,
            completed_date TEXT,
            url TEXT,
            title TEXT
        );
        CREATE TABLE human_users (
            id INTEGER PRIMARY KEY,
            last_locked TEXT
        );
        CREATE TABLE query_lock_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_schedule_id INTEGER,
            human_user_id INTEGER,
            thread_id INTEGER,
            action TEXT NOT NULL,
            event_time TEXT NOT NULL,
            previous_human_user_id INTEGER,
            previous_locked_at TEXT
        );
        """
    )

    query_columns = [
        "id",
        "pod_id",
        "country",
        "human_user_id",
        "scheduled_execution_date",
        "deletion_date",
        "priority",
        "locked_at",
    ]
    if not legacy:
        query_columns.append("locked_by_thread")

    def insert_query(values: tuple) -> None:
        placeholders = ", ".join("?" for _ in query_columns)
        columns = ", ".join(query_columns)
        connection.execute(
            f"INSERT INTO query_schedule ({columns}) VALUES ({placeholders})",
            values[: len(query_columns)],
        )

    insert_query(
        (
            100,
            3,
            "DE",
            None,
            (current_time + dt.timedelta(minutes=1)).isoformat(timespec="seconds"),
            None,
            90,
            None,
            None,
        )
    )
    insert_query(
        (
            101,
            3,
            "DE",
            None,
            (current_time + dt.timedelta(minutes=2)).isoformat(timespec="seconds"),
            None,
            80,
            None,
            None,
        )
    )
    insert_query(
        (
            150,
            3,
            "FR",
            77,
            (current_time + dt.timedelta(minutes=1)).isoformat(timespec="seconds"),
            None,
            100,
            (current_time - dt.timedelta(minutes=45)).strftime("%Y-%m-%d %H:%M:%S"),
            9,
        )
    )
    insert_query(
        (
            151,
            3,
            "FR",
            78,
            (current_time + dt.timedelta(minutes=1)).isoformat(timespec="seconds"),
            None,
            110,
            (current_time - dt.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S"),
            10,
        )
    )

    if legacy:
        connection.executemany(
            """
            INSERT INTO query_schedule_steps
                (id, query_schedule_id, type, value, completed_date, url, title)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (1, 100, "google_search", "best pasta berlin", None, None, None),
                (2, 100, "click_result", "any", None, None, None),
            ],
        )
    else:
        connection.executemany(
            """
            INSERT INTO query_schedule_steps
                (query_schedule_id, position, type, value, completed_date, url, title)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (100, 2, "click_result", "any", None, None, None),
                (100, 1, "google_search", "best pasta berlin", None, None, None),
            ],
        )

    connection.execute("INSERT INTO human_users (id, last_locked) VALUES (42, 'locked')")
    connection.commit()
    return connection


def build_memory_node_db() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(
        """
        CREATE TABLE nodes (
            uuid TEXT PRIMARY KEY,
            currently_online TEXT NOT NULL,
            country TEXT NOT NULL
        );
        CREATE TABLE nodes_to_human_users (
            node_uuid TEXT NOT NULL,
            human_user_id INTEGER NOT NULL
        );
        INSERT INTO nodes VALUES ('node-a', 'TRUE', 'DE');
        INSERT INTO nodes VALUES ('node-b', 'FALSE', 'FR');
        INSERT INTO nodes_to_human_users VALUES ('node-a', 42);
        INSERT INTO nodes_to_human_users VALUES ('node-a', 42);
        INSERT INTO nodes_to_human_users VALUES ('node-a', 44);
        INSERT INTO nodes_to_human_users VALUES ('node-b', 43);
        """
    )
    return connection
