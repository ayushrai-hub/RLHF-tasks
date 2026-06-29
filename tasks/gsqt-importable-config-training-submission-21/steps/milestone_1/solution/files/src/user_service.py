"""Human user locking helpers."""

from __future__ import annotations

from src.config.database import DatabaseOperations, get_query_engine


class UserService:
    """User service with lazy database access."""

    @staticmethod
    def unlock_user(user_id: int) -> None:
        DatabaseOperations.update_by_id(get_query_engine(), "human_users", user_id, last_locked=None)
