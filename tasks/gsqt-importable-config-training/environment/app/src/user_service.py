"""Human user locking helpers."""

from __future__ import annotations

from src.config.database import DatabaseOperations, get_query_engine


query_engine = get_query_engine()


class UserService:
    """User service with hard-wired database access."""

    @staticmethod
    def unlock_user(user_id: int) -> None:
        DatabaseOperations.update_by_id(query_engine, "human_users", user_id, last_locked=None)
