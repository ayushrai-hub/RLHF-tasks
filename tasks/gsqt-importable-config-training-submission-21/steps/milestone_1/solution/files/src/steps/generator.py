"""Build executable step dictionaries from scheduled query rows."""

from __future__ import annotations

from typing import Any

from src.config.database import get_query_engine


class StepBuilder:
    """Loads query steps with lazy database access."""

    def __init__(self, country_node: str | None = None, human_user_id: int | None = None):
        self.country_node = country_node
        self.human_user_id = human_user_id

    def build_query_steps(self, selected_query: dict[str, Any]) -> list[dict[str, Any]]:
        query_engine = get_query_engine()
        query_schedule_id = selected_query["id"]
        rows = query_engine.execute(
            """
            SELECT type, value, completed_date, url, title
            FROM query_schedule_steps
            WHERE query_schedule_id = ?
            ORDER BY id
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
