from __future__ import annotations
from datetime import datetime
from typing import Callable, TypeVar

T = TypeVar("T")


class RateLimitExceeded(Exception):
    pass


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(
        self,
        capacity: int = 10,
        refill_rate: float = 1.0,
        time_fn: Callable[[], datetime] | None = None,
    ) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._time_fn = time_fn or datetime.utcnow
        self._tokens: float = float(capacity)
        self._last_refill: datetime = self._time_fn()

    def execute(self, fn: Callable[[], T]) -> T:
        self._refill()
        if self._tokens < 1.0:
            raise RateLimitExceeded("Rate limit exceeded — no tokens available")
        self._tokens -= 1.0
        return fn()

    def available_tokens(self) -> int:
        self._refill()
        return int(self._tokens)

    def _refill(self) -> None:
        now = self._time_fn()
        elapsed = (now - self._last_refill).total_seconds()
        self._tokens += elapsed * self.refill_rate
        self._last_refill = now
