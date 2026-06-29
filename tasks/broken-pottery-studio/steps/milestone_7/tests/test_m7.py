from __future__ import annotations
import sys
sys.path.append('/app')
import pytest
from datetime import datetime
from data import Address, Section
from studio import Studio, ClassSession
from student import Student
from reservation_system import ReservationSystem, ReservationError
from refund_policy import RefundPolicy


def _make_refund_system() -> ReservationSystem:
    system = ReservationSystem()
    venue = Studio(
        studio_id="V1",
        name="Test Studio",
        address=Address("1 Main St", "City", "ST", "00000"),
        sections=[Section("A", 4, ["A1", "A2", "A3", "A4"])],
        max_occupancy=4,
    )
    event = ClassSession(class_session_id="E1", studio=venue, time=datetime(2099, 6, 14, 10, 0, 0))
    customer = Student(
        student_id="C1",
        name="Test",
        age=30,
        address=Address("1 Main St", "City", "ST", "00000"),
    )
    system.add_class_session(event)
    system.add_student(customer)
    return system


def _make_system() -> ReservationSystem:
    system = ReservationSystem()
    venue = Studio(
        studio_id="V1",
        name="Test Studio",
        address=Address("1 Main St", "City", "ST", "00000"),
        sections=[
            Section("F", 5, ["F1", "F2", "F3", "F4", "F5"]),
            Section("G", 5, ["G1", "G2", "G3", "G4", "G5"]),
        ],
        max_occupancy=10,
    )
    event = ClassSession(class_session_id="E1", studio=venue, time=datetime(2099, 6, 14, 10, 0, 0))
    customer = Student(
        student_id="C1",
        name="Test",
        age=30,
        address=Address("1 Main St", "City", "ST", "00000"),
    )
    system.add_class_session(event)
    system.add_student(customer)
    return system


class TestRefundPolicyRules:

    def test_partial_cancellation_refund_reflects_returned_wheel_share(self) -> None:
        """Returning half the wheels in a booking should refund half the full cancellation amount."""
        class FakeTxn:
            has_cancellation_coverage = True
            reservation_id = "T1"
            def get_resources(self) -> list[str]:
                return ["A1", "A2", "A3", "A4"]
            created_at = datetime(2099, 6, 13, 10, 0, 0)
            non_refundable_amount = 0.0
            def get_total_paid(self) -> float:
                return 100.0
        policy = RefundPolicy()
        full_result = policy.calculate(FakeTxn(), datetime(2099, 6, 14, 10, 0, 0))
        partial_result = policy.calculate_prorated(FakeTxn(), datetime(2099, 6, 14, 10, 0, 0), ["A1", "A2"])
        assert abs(partial_result.refund_amount - full_result.refund_amount * 0.5) < 0.01

    def test_cancel_without_coverage_gives_no_refund(self) -> None:
        """Cancelling a reservation without cancellation coverage must return a zero refund."""
        system = _make_refund_system()
        txn = system.book_wheels("C1", "E1", ["A1"])
        result = system.cancel_reservation(txn.reservation_id)
        assert result.refund_amount == 0.0

    def test_cancel_with_coverage_gives_refund(self) -> None:
        """Cancelling a reservation with cancellation coverage must return a non-zero refund."""
        system = _make_refund_system()
        txn = system.book_wheels("C1", "E1", ["A1"])
        txn.has_cancellation_coverage = True
        result = system.cancel_reservation(txn.reservation_id)
        assert result.refund_amount > 0.0


class TestCustomerTicketRules:

    def test_cumulative_tickets_exceed_limit(self) -> None:
        """After two reservations whose combined total exceeds the limit, a third must be rejected."""
        system = _make_system()
        system.book_wheels("C1", "E1", ["F1", "F2", "F3", "F4", "F5"])
        system.book_wheels("C1", "E1", ["G1", "G2", "G3", "G4"])
        with pytest.raises(ReservationError):
            system.book_wheels("C1", "E1", ["G5"])

    def test_first_reservation_within_limit_succeeds(self) -> None:
        """A first reservation within the wheel limit must succeed."""
        system = _make_system()
        txn = system.book_wheels("C1", "E1", ["F1", "F2"])
        assert txn is not None


class TestCustomerLimitRules:

    def test_reservation_blocked_at_exact_limit(self) -> None:
        """A reservation must be rejected when the student has exactly reached the per-class_session wheel limit."""
        system = _make_system()
        system.book_wheels(
            "C1", "E1", ["F1", "F2", "F3", "F4", "F5", "G1", "G2", "G3"]
        )
        with pytest.raises(ReservationError):
            system.book_wheels("C1", "E1", ["G4"])

    def test_reservation_allowed_below_limit(self) -> None:
        """A reservation must succeed when the student is below the per-class_session wheel limit."""
        system = _make_system()
        txn = system.book_wheels("C1", "E1", ["F1", "F2", "F3"])
        assert txn is not None
