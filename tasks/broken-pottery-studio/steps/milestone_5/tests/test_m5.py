from __future__ import annotations
import sys
sys.path.append('/app')
import pytest
from datetime import datetime
from data import Address, Section
from studio import Studio, ClassSession
from student import Student
from reservation import Reservation, InvalidStateTransition
from reservation_system import ReservationSystem


def _make_waitlist_system() -> ReservationSystem:
    sections = [Section("Main", 4, ["S1", "S2", "S3", "S4"])]
    venue = Studio(
        studio_id="V1", name="Test", address=Address("1 Main", "City", "ST", "00000"),
        sections=sections, max_occupancy=4,
    )
    event = ClassSession(class_session_id="E1", studio=venue, time=datetime(2030, 6, 3, 14, 0))
    system = ReservationSystem()
    system.add_class_session(event)
    for i, tier in enumerate(["standard", "gold", "standard", "standard"], 1):
        c = Student(student_id=f"C{i}", name=f"Customer {i}", age=30,
                    address=Address("1 Main", "City", "ST", "00000"),
                    loyalty_tier=tier)
        system.add_student(c)
    return system


def _make_txn(status: str = "pending") -> Reservation:
    t = Reservation(
        reservation_id="T1",
        student_id="C1",
        class_session_id="E1",
        wheels=["A1"],
        total_price=100.0,
    )
    if status == "confirmed":
        t.confirm()
    elif status == "cancellation_requested":
        t.confirm()
        t.request_cancellation()
    return t


class TestWaitlistPromotionRules:

    def test_premium_tier_student_promoted_before_standard_tier(self) -> None:
        """A gold-tier student must be promoted ahead of a standard-tier student regardless of who joined the waitlist first."""
        system = _make_waitlist_system()
        system.add_to_waitlist("C1", "E1")
        system.add_to_waitlist("C2", "E1")
        promoted = system.promote_from_waitlist("E1")
        assert promoted == "C2"

    def test_students_at_same_tier_promoted_in_join_order(self) -> None:
        """Within the same loyalty tier, the earliest student to join the waitlist is promoted first."""
        system = _make_waitlist_system()
        system.add_to_waitlist("C1", "E1")
        system.add_to_waitlist("C3", "E1")
        assert system.promote_from_waitlist("E1") == "C1"
        assert system.promote_from_waitlist("E1") == "C3"

    def test_first_student_on_waitlist_has_immediate_next_position(self) -> None:
        """The student next in line to be promoted must be reported at position one."""
        system = _make_waitlist_system()
        system.add_to_waitlist("C1", "E1")
        system.add_to_waitlist("C3", "E1")
        assert system.get_waitlist_position("C1", "E1") == 1

    def test_waitlist_positions_shift_after_promotion(self) -> None:
        """After a student is promoted, the remaining students move up one position each."""
        system = _make_waitlist_system()
        system.add_to_waitlist("C1", "E1")
        system.add_to_waitlist("C3", "E1")
        system.add_to_waitlist("C4", "E1")
        assert system.get_waitlist_position("C3", "E1") == 2
        system.promote_from_waitlist("E1")
        assert system.get_waitlist_position("C3", "E1") == 1


class TestBookingCancellationRules:

    def test_unconfirmed_booking_cannot_be_cancelled(self) -> None:
        """A booking that has not yet been confirmed must not be reported as eligible for cancellation."""
        txn = _make_txn("pending")
        assert not txn.is_cancellable()

    def test_confirmed_booking_is_eligible_for_cancellation(self) -> None:
        """A confirmed booking must be reported as eligible for cancellation."""
        txn = _make_txn("confirmed")
        assert txn.is_cancellable()

    def test_booking_in_cancellation_review_remains_cancellable(self) -> None:
        """A booking whose cancellation is under review must still be reported as cancellable."""
        txn = _make_txn("cancellation_requested")
        assert txn.is_cancellable()

    def test_cancelling_unconfirmed_booking_raises_error(self) -> None:
        """Attempting to cancel a booking that has not been confirmed must raise an error."""
        txn = _make_txn("pending")
        with pytest.raises(InvalidStateTransition):
            txn.cancel()
