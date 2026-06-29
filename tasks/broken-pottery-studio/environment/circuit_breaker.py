from __future__ import annotations
from datetime import datetime
from typing import Callable, TypeVar

T = TypeVar("T")

ACTIVE = "active"
SUSPENDED = "suspended"
PROBING = "probing"

class GuardOpen(Exception):
    pass

class CircuitBreaker:
    """Circuit breaker with three states: active, suspended, and probing."""

    def __init__(
        self,
        failure_threshold: int = 3,
        suspension_timeout: float = 30.0,
        time_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.suspension_timeout = suspension_timeout
        self._time_fn = time_fn or datetime.utcnow
        self._state: str = ACTIVE
        self._failure_count: int = 0
        self._suspended_at: datetime | None = None

    @property
    def state(self) -> str:
        return self._state

    def execute(self, fn: Callable[[], T]) -> T:
        self._evaluate_state()
        if self._state == SUSPENDED:
            raise GuardOpen("Circuit breaker is open — calls suspended")
        try:
            result = fn()
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _evaluate_state(self) -> None:
        if self._state == SUSPENDED:
            elapsed = (self._time_fn() - self._suspended_at).total_seconds()
            if elapsed >= self.suspension_timeout:
                self._state = PROBING

    def _on_success(self) -> None:
        self._failure_count = 0
        self._state = ACTIVE
        self._suspended_at = None

    def _on_failure(self) -> None:
        self._failure_count += 1
        if self._state == PROBING:
            self._state = SUSPENDED
        elif self._failure_count >= self.failure_threshold:
            self._state = SUSPENDED
            if self._suspended_at is None:
                self._suspended_at = self._time_fn()
