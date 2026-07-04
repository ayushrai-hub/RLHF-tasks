"""Human user locking helpers."""

from __future__ import annotations

import sqlite3

from src.config.database import DatabaseOperations, get_query_engine


class UserService:
    """User service with injectable database access."""

    def __init__(self, query_engine: sqlite3.Connection | None = None):
        self._query_engine = query_engine

    @property
    def query_engine(self) -> sqlite3.Connection:
        return self._query_engine or get_query_engine()

    def unlock_user(self, user_id: int) -> None:
        DatabaseOperations.update_by_id(self.query_engine, "human_users", user_id, last_locked=None)
