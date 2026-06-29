from __future__ import annotations
import sys
sys.path.append('/app')
import pytest
from datetime import datetime, timedelta
from studio_gateway import (
    StudioGateway, GatewayThrottled, GatewayUnavailable,
    ACTIVE, SUSPENDED, PROBING, RetryExhausted,
)
from retry import Retry
from pagination import Paginator


def _make_gateway(
    threshold: int = 3,
    timeout: float = 30.0,
    capacity: int = 100,
    refill: float = 10.0,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> tuple[StudioGateway, list[datetime]]:
    clock = [datetime(2024, 1, 1, 12, 0, 0)]
    gw = StudioGateway(
        failure_threshold=threshold,
        suspension_timeout=timeout,
        rate_capacity=capacity,
        rate_refill=refill,
        max_retries=max_retries,
        base_delay=base_delay,
        time_fn=lambda: clock[0],
        sleep_fn=lambda _: None,
    )
    return gw, clock


class TestGatewayResilienceRules:

    def test_gateway_allows_calls_when_service_healthy(self) -> None:
        """Calls through the gateway succeed when the downstream service responds normally."""
        gw, _ = _make_gateway()
        assert gw.call(lambda: "ok") == "ok"
        assert gw.guard_state == ACTIVE

    def test_gateway_suspends_after_service_failure_threshold(self) -> None:
        """Gateway stops forwarding calls after consecutive service failures reach the threshold."""
        gw, _ = _make_gateway(threshold=3)
        for _ in range(3):
            with pytest.raises(ValueError):
                gw.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert gw.guard_state == SUSPENDED

    def test_gateway_raises_unavailable_when_suspended(self) -> None:
        """Calls through a suspended gateway raise GatewayUnavailable instead of forwarding."""
        gw, _ = _make_gateway(threshold=1)
        with pytest.raises(ValueError):
            gw.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        with pytest.raises(GatewayUnavailable):
            gw.call(lambda: "should not reach")

    def test_gateway_probes_service_after_suspension_expires(self) -> None:
        """After the suspension window elapses, the gateway allows a probe call to test recovery."""
        gw, clock = _make_gateway(threshold=1, timeout=30.0)
        with pytest.raises(ValueError):
            gw.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        clock[0] += timedelta(seconds=31)
        gw.evaluate_guard()
        assert gw.guard_state == PROBING

    def test_gateway_restores_service_after_successful_probe(self) -> None:
        """A probe call that succeeds transitions the gateway back to normal forwarding."""
        gw, clock = _make_gateway(threshold=1, timeout=30.0)
        with pytest.raises(ValueError):
            gw.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        clock[0] += timedelta(seconds=31)
        result = gw.call(lambda: "recovered")
        assert result == "recovered"
        assert gw.guard_state == ACTIVE

    def test_gateway_failed_probe_resets_suspension_timer(self) -> None:
        """A failed probe must restart the suspension window from the probe time, not the original suspension."""
        gw, clock = _make_gateway(threshold=1, timeout=30.0)
        with pytest.raises(ValueError):
            gw.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert gw.guard_state == SUSPENDED
        clock[0] += timedelta(seconds=31)
        gw.evaluate_guard()
        assert gw.guard_state == PROBING
        with pytest.raises(ValueError):
            gw.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert gw.guard_state == SUSPENDED
        gw.evaluate_guard()
        assert gw.guard_state == SUSPENDED


class TestGatewayTrafficRules:

    def test_gateway_allows_calls_within_rate_limit(self) -> None:
        """Calls within the configured rate limit are forwarded normally."""
        gw, _ = _make_gateway(capacity=5)
        results = [gw.call(lambda: "ok") for _ in range(5)]
        assert results == ["ok"] * 5

    def test_gateway_raises_throttled_when_rate_exceeded(self) -> None:
        """Calls that exceed the token budget raise GatewayThrottled."""
        gw, _ = _make_gateway(capacity=2)
        gw.call(lambda: None)
        gw.call(lambda: None)
        with pytest.raises(GatewayThrottled):
            gw.call(lambda: None)

    def test_gateway_token_budget_does_not_exceed_capacity(self) -> None:
        """Token budget never grows beyond the configured maximum, even after a long idle period."""
        gw, clock = _make_gateway(capacity=3, refill=1.0)
        clock[0] += timedelta(seconds=1000)
        assert gw.available_tokens() == 3

    def test_gateway_refills_tokens_over_time(self) -> None:
        """Gateway accepts new calls after enough time elapses to replenish the token budget."""
        gw, clock = _make_gateway(capacity=2, refill=1.0)
        gw.call(lambda: None)
        gw.call(lambda: None)
        clock[0] += timedelta(seconds=2)
        gw.call(lambda: None)

    def test_gateway_token_count_reflects_refill(self) -> None:
        """Available token count increases proportionally to elapsed time and refill rate."""
        gw, clock = _make_gateway(capacity=10, refill=2.0)
        for _ in range(10):
            gw.call(lambda: None)
        clock[0] += timedelta(seconds=3)
        assert gw.available_tokens() >= 6.0


class TestGatewayRetryRules:

    def test_resilient_call_succeeds_on_first_attempt(self) -> None:
        """A call that succeeds immediately is not retried."""
        gw, _ = _make_gateway()
        calls = 0

        def fn() -> str:
            nonlocal calls
            calls += 1
            return "ok"

        result = gw.resilient_call(fn)
        assert result == "ok"
        assert calls == 1

    def test_resilient_call_retries_after_transient_failure(self) -> None:
        """After a transient failure, the gateway retries the call automatically."""
        gw, _ = _make_gateway(max_retries=3)
        calls = 0

        def fn() -> str:
            nonlocal calls
            calls += 1
            if calls < 3:
                raise ValueError("transient")
            return "ok"

        result = gw.resilient_call(fn)
        assert result == "ok"
        assert calls == 3

    def test_resilient_call_raises_after_max_retries(self) -> None:
        """When every retry attempt fails, RetryExhausted is raised after the configured limit."""
        gw, _ = _make_gateway(max_retries=3)

        def fn() -> None:
            raise ValueError("always")

        with pytest.raises(RetryExhausted) as exc_info:
            gw.resilient_call(fn)
        assert exc_info.value.attempts == 3

    def test_resilient_call_applies_exponential_backoff(self) -> None:
        """Delay between retries doubles on each successive attempt."""
        delays: list[float] = []
        retry = Retry(max_attempts=3, base_delay=1.0, sleep_fn=delays.append)

        def fn() -> None:
            raise ValueError("fail")

        with pytest.raises(RetryExhausted):
            retry.execute(fn)

        assert len(delays) == 2
        assert delays[1] == delays[0] * 2

    def test_non_retryable_errors_are_raised_immediately(self) -> None:
        """Errors outside the retryable set propagate immediately without consuming retry attempts."""
        delays: list[float] = []
        retry = Retry(max_attempts=3, base_delay=1.0, retryable=(ValueError,), sleep_fn=delays.append)
        calls = 0

        def fn() -> None:
            nonlocal calls
            calls += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError):
            retry.execute(fn)

        assert calls == 1
        assert delays == []


class TestSessionCatalogPaginationRules:

    def setup_method(self) -> None:
        self.paginator: Paginator[int] = Paginator()
        self.items = list(range(1, 11))

    def test_paginating_all_pages_yields_every_item_once(self) -> None:
        """Iterating through all pages returns every catalog item exactly once with no gaps or repeats."""
        page_size = 3
        all_items: list[int] = []
        page_num = 1
        while True:
            page = self.paginator.paginate(self.items, page_num, page_size)
            all_items.extend(page.items)
            if not page.has_next:
                break
            page_num += 1
        assert sorted(all_items) == self.items

    def test_final_page_contains_remainder_items(self) -> None:
        """The last page holds the remaining items even when they are fewer than the page size."""
        page = self.paginator.paginate(self.items, page=4, page_size=3)
        assert page.items == [10]

    def test_page_count_covers_all_items_including_partial_last_page(self) -> None:
        """Total page count must account for a partial last page, not truncate it."""
        page = self.paginator.paginate(self.items, page=1, page_size=3)
        assert page.total_pages == 4

    def test_navigation_flags_accurate_on_middle_page(self) -> None:
        """A middle page reports both has_prev and has_next as true."""
        page = self.paginator.paginate(self.items, page=2, page_size=3)
        assert page.has_next is True
        assert page.has_prev is True
