from __future__ import annotations
import sys
sys.path.append('/app')
import pytest
from datetime import datetime
from data import Address, Section
from studio import Studio, ClassSession
from student import Student
from reservation_system import ReservationSystem, ReservationError
from lock_manager import LockManager, AcquireDebounced, LeaseNotFound, NotLeaseOwner


def _make_lm(debounce: int = 30) -> tuple[LockManager, list[datetime]]:
    clock = [datetime(2024, 1, 1, 12, 0, 0)]
    lm = LockManager(debounce_seconds=debounce, time_fn=lambda: clock[0])
    return lm, clock


def _make_venue_system() -> tuple[ReservationSystem, Studio, ClassSession, Student]:
    system = ReservationSystem()
    venue = Studio(
        studio_id="V1",
        name="Test Studio",
        address=Address("1 Main St", "City", "ST", "00000"),
        sections=[Section("A", 2, ["A1", "A2"]), Section("B", 2, ["B1", "B2"])],
        max_occupancy=4,
    )
    event = ClassSession(
        class_session_id="E1",
        studio=venue,
        time=datetime(2099, 6, 14, 10, 0, 0),
    )
    customer = Student(
        student_id="C1",
        name="Test",
        age=30,
        address=Address("1 Main St", "City", "ST", "00000"),
    )
    system.add_class_session(event)
    system.add_student(customer)
    return system, venue, event, customer


class TestLockRules:

    def test_releasing_lease_allows_immediate_re_acquisition(self) -> None:
        """Owner who releases a lease must be able to re-acquire immediately."""
        lm, clock = _make_lm(debounce=30)
        lm.acquire("R1", "owner-A", ttl_seconds=60)
        lm.release("R1", "owner-A")
        lm.acquire("R1", "owner-A", ttl_seconds=60)

    def test_failed_acquire_debounces_requester(self) -> None:
        """A failed acquire attempt debounces the requesting owner."""
        lm, clock = _make_lm(debounce=30)
        lm.acquire("R1", "owner-A", ttl_seconds=60)
        with pytest.raises(Exception):
            lm.acquire("R1", "owner-B", ttl_seconds=60)
        with pytest.raises(AcquireDebounced):
            lm.acquire("R1", "owner-B", ttl_seconds=60)

    def test_release_allows_waiting_student_to_acquire(self) -> None:
        """After the holder releases, a previously debounced owner can acquire."""
        lm, clock = _make_lm(debounce=30)
        lm.acquire("R1", "owner-A", ttl_seconds=60)
        with pytest.raises(Exception):
            lm.acquire("R1", "owner-B", ttl_seconds=60)
        lm.release("R1", "owner-A")
        lm.acquire("R1", "owner-B", ttl_seconds=60)

    def test_release_wrong_owner_raises(self) -> None:
        """Releasing a lease held by another owner raises NotLeaseOwner."""
        lm, _ = _make_lm()
        lm.acquire("R1", "owner-A", ttl_seconds=60)
        with pytest.raises(NotLeaseOwner):
            lm.release("R1", "owner-B")

    def test_release_nonexistent_raises(self) -> None:
        """Releasing a resource with no lease raises LeaseNotFound."""
        lm, _ = _make_lm()
        with pytest.raises(LeaseNotFound):
            lm.release("R1", "owner-A")


class TestVenueRules:

    def test_blocked_resource_not_bookable(self) -> None:
        """Reservation of a blocked resource must raise a reservation error."""
        system, venue, event, customer = _make_venue_system()
        venue.block("A1")
        with pytest.raises(ReservationError):
            system.book_wheels("C1", "E1", ["A1"])

    def test_unblocked_resource_is_bookable(self) -> None:
        """A resource that was blocked then unblocked must be bookable again."""
        system, venue, event, customer = _make_venue_system()
        venue.block("A1")
        venue.unblock("A1")
        txn = system.book_wheels("C1", "E1", ["A1"])
        assert txn is not None

    def test_unblocked_resource_does_not_block_others(self) -> None:
        """Blocking one resource must not affect availability of others."""
        system, venue, event, customer = _make_venue_system()
        venue.block("A1")
        txn = system.book_wheels("C1", "E1", ["A2"])
        assert txn is not None

    def test_blocked_wheel_excluded_from_section_availability(self) -> None:
        """A blocked wheel must not appear in section-scoped availability results."""
        system, venue, event, customer = _make_venue_system()
        venue.block("A1")
        available = venue.get_available_resources(section="A")
        assert "A1" not in available
        assert "A2" in available

    def test_blocked_wheel_excluded_from_full_studio_availability(self) -> None:
        """A blocked wheel must not appear in full-studio (no section filter) availability results."""
        system, venue, event, customer = _make_venue_system()
        venue.block("B1")
        available = venue.get_available_resources()
        assert "B1" not in available
        assert "A1" in available
        assert "A2" in available
        assert "B2" in available
