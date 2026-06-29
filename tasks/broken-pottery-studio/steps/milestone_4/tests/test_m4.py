from __future__ import annotations
import sys
sys.path.append('/app')
import pytest
from datetime import datetime, timedelta
from data import Address, Section
from studio import Studio, ClassSession
from student import Student
from reservation_system import ReservationSystem, ReservationError
from time_provider import TimeProvider
from cache import Cache


class _MockTimeProvider(TimeProvider):
    def __init__(self) -> None:
        self._now = datetime(2024, 1, 1, 12, 0, 0)

    def now(self) -> datetime:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += timedelta(seconds=seconds)


def _make_availability_system(time_provider: TimeProvider) -> tuple[ReservationSystem, ClassSession, Student]:
    sections = [Section("Main", 4, ["S1", "S2", "S3", "S4"])]
    venue = Studio(
        studio_id="V1", name="Test", address=Address("1 Main", "City", "ST", "00000"),
        sections=sections, max_occupancy=4,
    )
    event = ClassSession(class_session_id="E1", studio=venue, time=datetime(2030, 6, 2, 14, 0))
    c1 = Student(student_id="C1", name="Alice", age=30,
                 address=Address("1 Main", "City", "ST", "00000"))
    c2 = Student(student_id="C2", name="Bob", age=30,
                 address=Address("1 Main", "City", "ST", "00000"))
    system = ReservationSystem(time_provider=time_provider)
    system.add_class_session(event)
    system.add_student(c1)
    system.add_student(c2)
    return system, event, c1


def _make_cache(capacity: int = 10) -> tuple[Cache, list[datetime]]:
    clock = [datetime(2024, 1, 1, 12, 0, 0)]
    c = Cache(capacity=capacity, time_fn=lambda: clock[0])
    return c, clock


class TestWheelAvailabilityRules:

    def test_wheel_released_when_hold_period_expires(self) -> None:
        """A wheel held for a booking that was not completed must become available once the hold expires."""
        clock = _MockTimeProvider()
        system, event, _ = _make_availability_system(clock)
        system.availability.hold(event, ["S1"], ttl_seconds=30)
        clock.advance(31)
        txn = system.book_wheels("C1", "E1", ["S1"])
        assert txn.wheels == ["S1"]

    def test_multiple_wheels_released_when_holds_expire(self) -> None:
        """All wheels held under expired holds must become available simultaneously."""
        clock = _MockTimeProvider()
        system, event, _ = _make_availability_system(clock)
        system.availability.hold(event, ["S1"], ttl_seconds=10)
        system.availability.hold(event, ["S2"], ttl_seconds=10)
        clock.advance(11)
        txn = system.book_wheels("C1", "E1", ["S1", "S2"])
        assert set(txn.wheels) == {"S1", "S2"}

    def test_active_hold_blocks_booking_before_expiry(self) -> None:
        """A wheel under an active hold must not be bookable until the hold expires."""
        clock = _MockTimeProvider()
        system, event, _ = _make_availability_system(clock)
        system.availability.hold(event, ["S3"], ttl_seconds=60)
        clock.advance(30)
        with pytest.raises(ReservationError):
            system.book_wheels("C1", "E1", ["S3"])


class TestLookupCacheRules:

    def test_null_result_stored_and_served_without_re_fetching(self) -> None:
        """A loader that returns nothing should have its result cached so the loader is not called again."""
        cache, _ = _make_cache()
        calls = 0

        def loader() -> None:
            nonlocal calls
            calls += 1
            return None

        cache.get_or_set("k", loader)
        cache.get_or_set("k", loader)
        assert calls == 1

    def test_missing_entry_triggers_data_load(self) -> None:
        """A key not present in the cache causes the loader to be called to fetch the value."""
        cache, _ = _make_cache()
        calls = 0

        def loader() -> str:
            nonlocal calls
            calls += 1
            return "value"

        result = cache.get_or_set("k", loader)
        assert result == "value"
        assert calls == 1

    def test_subsequent_lookup_served_from_cache(self) -> None:
        """After the first lookup, subsequent lookups for the same key must not invoke the loader."""
        cache, _ = _make_cache()
        calls = 0

        def loader() -> str:
            nonlocal calls
            calls += 1
            return "value"

        cache.get_or_set("k", loader)
        result = cache.get_or_set("k", loader)
        assert result == "value"
        assert calls == 1

    def test_stale_entry_refreshed_after_expiry(self) -> None:
        """Once a cached entry's lifetime elapses, the next lookup must call the loader again."""
        cache, clock = _make_cache()
        calls = 0

        def loader() -> str:
            nonlocal calls
            calls += 1
            return "value"

        cache.get_or_set("k", loader, ttl_seconds=10)
        clock[0] += timedelta(seconds=11)
        cache.get_or_set("k", loader, ttl_seconds=10)
        assert calls == 2
