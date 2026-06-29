"""Fake-backed healthcheck for local GSQT service wiring."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sqlite3
from typing import Any

from src.node_service import NodeService
from src.query_scheduling.scheduler import QueryScheduler
from src.steps.generator import StepBuilder
from src.testing import fakes
from src.user_service import UserService


class _RaceOnceCursor:
    def __init__(self, cursor, connection: "_RaceOnceConnection"):
        self._cursor = cursor
        self._connection = connection

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is not None and not self._connection.race_applied:
            self._connection.race_applied = True
            self._connection.raced_query_id = row["id"]
            self._connection.base.execute(
                """
                UPDATE query_schedule
                SET human_user_id = ?, locked_at = ?, locked_by_thread = ?
                WHERE id = ?
                """,
                (
                    99,
                    self._connection.race_time.isoformat(timespec="seconds"),
                    77,
                    row["id"],
                ),
            )
            self._connection.base.commit()
        return row

    def __getattr__(self, name: str):
        return getattr(self._cursor, name)


class _RaceOnceConnection:
    def __init__(self, base: sqlite3.Connection, race_time: dt.datetime):
        self.base = base
        self.race_time = race_time
        self.race_applied = False
        self.raced_query_id: int | None = None

    def execute(self, sql: str, parameters=(), /):
        cursor = self.base.execute(sql, parameters)
        normalized = " ".join(sql.upper().split())
        if (
            normalized.startswith("SELECT")
            and " FROM QUERY_SCHEDULE " in f" {normalized} "
            and " ORDER BY " in f" {normalized} "
        ):
            return _RaceOnceCursor(cursor, self)
        return cursor

    def commit(self) -> None:
        self.base.commit()

    def __getattr__(self, name: str):
        return getattr(self.base, name)


def _has_column(connection: sqlite3.Connection, table: str, column: str) -> bool:
    return column in {row["name"] for row in connection.execute(f"PRAGMA table_info({table})")}


def _lock_event_actions(connection: sqlite3.Connection) -> list[str]:
    event_table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'query_lock_events'"
    ).fetchone()
    if event_table is None:
        return []
    return [
        row["action"]
        for row in connection.execute("SELECT action FROM query_lock_events ORDER BY id")
    ]


def _run_query_checks(query_db: sqlite3.Connection, now: dt.datetime) -> dict[str, Any]:
    scheduler = QueryScheduler(query_engine=query_db)
    selected, camo = scheduler.get_and_lock_query(
        "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=21
    )
    steps = StepBuilder(query_engine=query_db).build_query_steps(selected) if selected else []
    stale_selected, stale_camo = scheduler.get_and_lock_query(
        "FR", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=22
    )

    selected_id = selected["id"] if selected else None
    if selected_id is not None:
        scheduler.unlock_query(selected_id)
    UserService(query_engine=query_db).unlock_user(42)

    query_unlocked = None
    if selected_id is not None:
        query_unlocked = (
            query_db.execute(
                "SELECT human_user_id FROM query_schedule WHERE id = ?", (selected_id,)
            ).fetchone()[0]
            is None
        )
    user_unlocked = query_db.execute(
        "SELECT last_locked FROM human_users WHERE id = 42"
    ).fetchone()[0] is None

    return {
        "selected_query_id": selected_id,
        "camo_query": camo,
        "loaded_step_types": [step["type"] for step in steps],
        "query_unlocked": query_unlocked,
        "user_unlocked": user_unlocked,
        "stale_query_claimed": (
            not stale_camo and stale_selected and stale_selected["id"] == 150
        ),
        "lock_event_actions": _lock_event_actions(query_db),
        "locked_by_thread_supported": _has_column(
            query_db, "query_schedule", "locked_by_thread"
        ),
    }


def _run_retry_check(now: dt.datetime) -> dict[str, Any]:
    query_db = fakes.build_memory_query_db(now=now)
    race_connection = _RaceOnceConnection(query_db, now + dt.timedelta(seconds=1))
    scheduler = QueryScheduler(query_engine=race_connection)
    selected, camo = scheduler.get_and_lock_query(
        "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=50
    )
    return {
        "race_applied": race_connection.race_applied,
        "raced_query_id": race_connection.raced_query_id,
        "selected_query_id": selected["id"] if selected else None,
        "camo_query": camo,
        "lock_event_actions": _lock_event_actions(query_db),
    }


def _run_auditless_check(now: dt.datetime) -> dict[str, Any]:
    query_db = fakes.build_memory_query_db(now=now)
    query_db.execute("DROP TABLE query_lock_events")
    query_db.commit()
    scheduler = QueryScheduler(query_engine=query_db)
    selected, camo = scheduler.get_and_lock_query(
        "DE", {"human_user_id": 42, "pod_id": 3}, now=now, thread_id=60
    )
    selected_id = selected["id"] if selected else None
    if selected_id is not None:
        scheduler.unlock_query(selected_id)
    query_unlocked = None
    if selected_id is not None:
        query_unlocked = (
            query_db.execute(
                "SELECT human_user_id FROM query_schedule WHERE id = ?", (selected_id,)
            ).fetchone()[0]
            is None
        )
    return {
        "selected_query_id": selected_id,
        "camo_query": camo,
        "query_unlocked": query_unlocked,
        "lock_event_actions": _lock_event_actions(query_db),
    }


def run_healthcheck() -> dict[str, Any]:
    now = dt.datetime(2026, 1, 1, 12, 0, 0)
    modern = _run_query_checks(fakes.build_memory_query_db(now=now), now)
    legacy = _run_query_checks(fakes.build_memory_query_db(now=now, legacy=True), now)
    retry_report = _run_retry_check(now)
    auditless_report = _run_auditless_check(now)
    node_db = fakes.build_memory_node_db()
    online_nodes, user_pool = NodeService(node_engine=node_db).get_online_nodes_and_user_pool()

    return {
        "imported": True,
        "selected_query_id": modern["selected_query_id"],
        "camo_query": modern["camo_query"],
        "loaded_step_types": modern["loaded_step_types"],
        "query_unlocked": modern["query_unlocked"],
        "user_unlocked": modern["user_unlocked"],
        "online_node_count": len(online_nodes),
        "stale_query_claimed": modern["stale_query_claimed"],
        "node_user_count": len(user_pool),
        "lock_event_actions": modern["lock_event_actions"],
        "retry_report": retry_report,
        "auditless_report": auditless_report,
        "schema_reports": {
            "modern": modern,
            "legacy": legacy,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    args = parser.parse_args(argv)

    report = run_healthcheck()
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        for key, value in report.items():
            print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
