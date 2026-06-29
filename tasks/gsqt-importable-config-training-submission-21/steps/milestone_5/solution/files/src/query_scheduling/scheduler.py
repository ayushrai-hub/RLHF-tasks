"""Scheduled query selection and result locking."""

from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Any

from src.config.database import DatabaseOperations, get_query_engine


class QueryScheduler:
    """Query scheduler with injectable database access."""

    def __init__(self, query_engine: sqlite3.Connection | None = None):
        self._query_engine = query_engine

    @property
    def query_engine(self) -> sqlite3.Connection:
        return self._query_engine or get_query_engine()

    def _columns(self, table: str) -> set[str]:
        return {row["name"] for row in self.query_engine.execute(f"PRAGMA table_info({table})")}

    def _has_table(self, table: str) -> bool:
        row = self.query_engine.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        return row is not None

    def _record_lock_event(
        self,
        query_schedule_id: int,
        human_user_id: int | None,
        thread_id: int | None,
        action: str,
        event_time: str,
        previous_human_user_id: int | None = None,
        previous_locked_at: str | None = None,
    ) -> None:
        if not self._has_table("query_lock_events"):
            return
        self.query_engine.execute(
            """
            INSERT INTO query_lock_events
                (query_schedule_id, human_user_id, thread_id, action, event_time,
                 previous_human_user_id, previous_locked_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                query_schedule_id,
                human_user_id,
                thread_id,
                action,
                event_time,
                previous_human_user_id,
                previous_locked_at,
            ),
        )

    def get_and_lock_query(
        self,
        country_node: str,
        human_user: dict[str, Any],
        now: dt.datetime | None = None,
        thread_id: int | None = None,
        lock_ttl_minutes: int = 15,
    ) -> tuple[dict[str, Any] | None, bool]:
        current_time = now or dt.datetime.now()
        window_end = current_time + dt.timedelta(minutes=10)
        stale_before = current_time - dt.timedelta(minutes=lock_ttl_minutes)

        now_text = current_time.isoformat(timespec="seconds")
        window_end_text = window_end.isoformat(timespec="seconds")
        stale_before_text = stale_before.isoformat(timespec="seconds")
        has_locked_by_thread = "locked_by_thread" in self._columns("query_schedule")

        while True:
            row = self.query_engine.execute(
                """
                SELECT *
                FROM query_schedule
                WHERE replace(scheduled_execution_date, ' ', 'T') >= ?
                  AND replace(scheduled_execution_date, ' ', 'T') <= ?
                  AND country = ?
                  AND pod_id = ?
                  AND deletion_date IS NULL
                  AND (
                        human_user_id IS NULL
                        OR (locked_at IS NOT NULL AND replace(locked_at, ' ', 'T') < ?)
                      )
                ORDER BY priority DESC, replace(scheduled_execution_date, ' ', 'T') ASC, id ASC
                LIMIT 1
                """,
                (
                    now_text,
                    window_end_text,
                    country_node,
                    human_user["pod_id"],
                    stale_before_text,
                ),
            ).fetchone()

            if row is None:
                return None, True

            assignments = ["human_user_id = ?", "locked_at = ?"]
            update_values: list[Any] = [
                human_user["human_user_id"],
                now_text,
            ]
            if has_locked_by_thread:
                assignments.append("locked_by_thread = ?")
                update_values.append(thread_id)
            update_values.extend(
                [
                    row["id"],
                    now_text,
                    window_end_text,
                    country_node,
                    human_user["pod_id"],
                    stale_before_text,
                ]
            )

            cursor = self.query_engine.execute(
                f"""
                UPDATE query_schedule
                SET {", ".join(assignments)}
                WHERE id = ?
                  AND replace(scheduled_execution_date, ' ', 'T') >= ?
                  AND replace(scheduled_execution_date, ' ', 'T') <= ?
                  AND country = ?
                  AND pod_id = ?
                  AND deletion_date IS NULL
                  AND (
                        human_user_id IS NULL
                        OR (locked_at IS NOT NULL AND replace(locked_at, ' ', 'T') < ?)
                      )
                """,
                update_values,
            )
            if cursor.rowcount == 1:
                action = "reclaim" if row["human_user_id"] is not None else "claim"
                self._record_lock_event(
                    row["id"],
                    human_user["human_user_id"],
                    thread_id,
                    action,
                    now_text,
                    row["human_user_id"],
                    row["locked_at"],
                )
                self.query_engine.commit()
                return dict(row), False

            self._record_lock_event(
                row["id"],
                human_user["human_user_id"],
                thread_id,
                "race_miss",
                now_text,
                row["human_user_id"],
                row["locked_at"],
            )
            self.query_engine.commit()

    def unlock_query(self, query_id: int) -> None:
        fields: dict[str, Any] = {
            "human_user_id": None,
            "locked_at": None,
        }
        if "locked_by_thread" in self._columns("query_schedule"):
            fields["locked_by_thread"] = None
        DatabaseOperations.update_by_id(
            self.query_engine,
            "query_schedule",
            query_id,
            **fields,
        )
        self._record_lock_event(
            query_id,
            None,
            None,
            "unlock",
            dt.datetime.now().isoformat(timespec="seconds"),
        )
        self.query_engine.commit()
