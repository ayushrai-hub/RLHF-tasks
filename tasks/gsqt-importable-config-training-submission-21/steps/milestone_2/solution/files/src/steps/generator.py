"""Build executable step dictionaries from scheduled query rows."""

from __future__ import annotations

import sqlite3
from typing import Any

from src.config.database import get_query_engine


class StepBuilder:
    """Loads query steps with injectable database access."""

    def __init__(
        self,
        country_node: str | None = None,
        human_user_id: int | None = None,
        query_engine: sqlite3.Connection | None = None,
    ):
        self.country_node = country_node
        self.human_user_id = human_user_id
        self._query_engine = query_engine

    @property
    def query_engine(self) -> sqlite3.Connection:
        return self._query_engine or get_query_engine()

    def build_query_steps(self, selected_query: dict[str, Any]) -> list[dict[str, Any]]:
        query_schedule_id = selected_query["id"]
        columns = {
            row["name"] for row in self.query_engine.execute("PRAGMA table_info(query_schedule_steps)")
        }
        order_clause = "position IS NULL, position, id" if "position" in columns else "id"
        rows = self.query_engine.execute(
            f"""
            SELECT type, value, completed_date, url, title
            FROM query_schedule_steps
            WHERE query_schedule_id = ?
            ORDER BY {order_clause}
            """,
            (query_schedule_id,),
        ).fetchall()

        steps: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            steps.append(
                {
                    "step_number": index,
                    "type": row["type"],
                    "value": row["value"],
                    "done": row["completed_date"],
                    "url": row["url"],
                    "title": row["title"],
                }
            )
        return steps
