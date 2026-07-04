"""Database configuration for the stripped-down GSQT scheduler.

The current version mirrors a common failure in the original project: importing
database configuration immediately reads production environment variables and
opens connections. The milestones ask you to make this import-safe and
testable.
"""

from __future__ import annotations

import os
import sqlite3
from typing import Any


QUERY_DSN = os.environ["GSQT_QUERY_DSN"]
NODE_DSN = os.environ["GSQT_NODE_DSN"]

query_engine = sqlite3.connect(QUERY_DSN)
query_engine.row_factory = sqlite3.Row
node_engine = sqlite3.connect(NODE_DSN)
node_engine.row_factory = sqlite3.Row


def get_query_engine() -> sqlite3.Connection:
    return query_engine


def get_node_engine() -> sqlite3.Connection:
    return node_engine


class DatabaseOperations:
    """Small SQL helper used by services in this task."""

    @staticmethod
    def update_by_id(connection: sqlite3.Connection, table: str, record_id: int, **fields: Any) -> None:
        if not fields:
            return
        assignments = ", ".join(f"{column} = ?" for column in fields)
        values = list(fields.values())
        values.append(record_id)
        connection.execute(f"UPDATE {table} SET {assignments} WHERE id = ?", values)
        connection.commit()
