from __future__ import annotations
from datetime import datetime
from typing import Callable, TypeVar

from circuit_breaker import CircuitBreaker, GuardOpen, ACTIVE, SUSPENDED, PROBING
from rate_limiter import RateLimiter, RateLimitExceeded
from retry import Retry, RetryExhausted

T = TypeVar("T")

__all__ = [
    "StudioGateway",
    "GatewayThrottled",
    "GatewayUnavailable",
    "ACTIVE",
    "SUSPENDED",
    "PROBING",
    "RetryExhausted",
]


class GatewayThrottled(Exception):
    pass


class GatewayUnavailable(Exception):
    pass


class StudioGateway:
    """
    Reliability wrapper that applies rate limiting, circuit breaking, and retry
    logic to outbound service calls during the studio booking workflow.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        suspension_timeout: float = 60.0,
        rate_capacity: int = 100,
        rate_refill: float = 10.0,
        max_retries: int = 3,
        base_delay: float = 1.0,
        time_fn: Callable[[], datetime] | None = None,
        sleep_fn: Callable[[float], None] | None = None,
    ) -> None:
        self._guard = CircuitBreaker(
            failure_threshold=failure_threshold,
            suspension_timeout=suspension_timeout,
            time_fn=time_fn,
        )
        self._gate = RateLimiter(
            capacity=rate_capacity,
            refill_rate=rate_refill,
            time_fn=time_fn,
        )
        self._retry = Retry(
            max_attempts=max_retries,
            base_delay=base_delay,
            sleep_fn=sleep_fn or (lambda _: None),
        )

    @property
    def guard_state(self) -> str:
        return self._guard.state

    def available_tokens(self) -> float:
        return self._gate.available_tokens()

    def evaluate_guard(self) -> None:
        self._guard._evaluate_state()

    def call(self, fn: Callable[[], T]) -> T:
        """Execute a call with rate-limiter then circuit-breaker protection."""
        try:
            return self._gate.execute(lambda: self._guard.execute(fn))
        except RateLimitExceeded as exc:
            raise GatewayThrottled("Request rate exceeded") from exc
        except GuardOpen as exc:
            raise GatewayUnavailable("Service temporarily unavailable") from exc

    def resilient_call(self, fn: Callable[[], T]) -> T:
        """Execute a call with automatic retry and exponential back-off."""
        return self._retry.execute(fn)
