from __future__ import annotations
import time
from typing import Callable, TypeVar

T = TypeVar("T")


class RetryExhausted(Exception):
    def __init__(self, attempts: int, last_error: Exception) -> None:
        super().__init__(f"Failed after {attempts} attempt(s): {last_error}")
        self.attempts = attempts
        self.last_error = last_error


class Retry:
    """Retry wrapper with exponential backoff."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        retryable: tuple[type[Exception], ...] = (Exception,),
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.retryable = retryable
        self._sleep = sleep_fn if sleep_fn is not None else time.sleep

    def execute(self, fn: Callable[[], T]) -> T:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return fn()
            except self.retryable as exc:
                last_error = exc
                if attempt < self.max_attempts:
                    self._sleep(self.base_delay)
        assert last_error is not None
        raise RetryExhausted(self.max_attempts, last_error)
