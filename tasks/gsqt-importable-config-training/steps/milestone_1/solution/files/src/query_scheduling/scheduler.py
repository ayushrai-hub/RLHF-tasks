"""Scheduled query selection and result locking."""

from __future__ import annotations

import datetime as dt
from typing import Any

from src.config.database import DatabaseOperations, get_query_engine


class QueryScheduler:
    """Query scheduler with lazy database access."""

    @staticmethod
    def get_and_lock_query(
        country_node: str,
        human_user: dict[str, Any],
        now: dt.datetime | None = None,
    ) -> tuple[dict[str, Any] | None, bool]:
        query_engine = get_query_engine()
        current_time = now or dt.datetime.now()
        window_end = current_time + dt.timedelta(minutes=10)

        row = query_engine.execute(
            """
            SELECT *
            FROM query_schedule
            WHERE scheduled_execution_date >= ?
              AND scheduled_execution_date <= ?
              AND country = ?
              AND pod_id = ?
              AND human_user_id IS NULL
              AND deletion_date IS NULL
            ORDER BY scheduled_execution_date ASC, id ASC
            LIMIT 1
            """,
            (
                current_time.isoformat(timespec="seconds"),
                window_end.isoformat(timespec="seconds"),
                country_node,
                human_user["pod_id"],
            ),
        ).fetchone()

        if row is None:
            return None, True

        query_engine.execute(
            "UPDATE query_schedule SET human_user_id = ? WHERE id = ?",
            (human_user["human_user_id"], row["id"]),
        )
        query_engine.commit()
        return dict(row), False

    @staticmethod
    def unlock_query(query_id: int) -> None:
        DatabaseOperations.update_by_id(get_query_engine(), "query_schedule", query_id, human_user_id=None)
