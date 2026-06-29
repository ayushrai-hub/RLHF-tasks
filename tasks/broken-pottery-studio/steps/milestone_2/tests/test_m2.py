from __future__ import annotations
import sys
sys.path.append('/app')
from datetime import datetime, timedelta
from data import Address, Section
from studio import Studio, ClassSession
from student import Student
from reservation_system import ReservationSystem


def _future_weekday(weekday: int, hour: int) -> datetime:
    """Return a far-future datetime with the given weekday (0=Mon, 6=Sun) and hour."""
    base = datetime(2099, 1, 1, hour, 0, 0)
    days_ahead = (weekday - base.weekday()) % 7
    return base + timedelta(days=days_ahead)


def _make_event_pricing_system(weekday: int, hour: int) -> ReservationSystem:
    system = ReservationSystem()
    venue = Studio(
        studio_id="V1",
        name="Test Studio",
        address=Address("1 Main St", "City", "ST", "00000"),
        sections=[Section("F", 4, ["F1", "F2", "F3", "F4"])],
        max_occupancy=4,
    )
    event = ClassSession(class_session_id="E1", studio=venue, time=_future_weekday(weekday, hour))
    customer = Student(
        student_id="C1",
        name="Test",
        age=30,
        address=Address("1 Main St", "City", "ST", "00000"),
    )
    system.add_class_session(event)
    system.add_student(customer)
    return system


class TestEventPricingRules:

    def test_weekday_evening_not_peak(self) -> None:
        """Reservation of a single wheel on a weekday evening must use regular pricing."""
        system = _make_event_pricing_system(weekday=0, hour=19)
        txn = system.book_wheels("C1", "E1", ["F1"])
        expected = 30.0 * (1 + 0.08)
        assert abs(txn.total_price - expected) < 0.01

    def test_weekend_morning_not_peak(self) -> None:
        """Reservation of a single wheel on a weekend morning must use regular pricing."""
        system = _make_event_pricing_system(weekday=5, hour=10)
        txn = system.book_wheels("C1", "E1", ["F1"])
        expected = 30.0 * (1 + 0.08)
        assert abs(txn.total_price - expected) < 0.01

    def test_weekend_evening_is_peak(self) -> None:
        """Reservation of a single wheel on a weekend evening must apply the 1.2x peak multiplier."""
        system = _make_event_pricing_system(weekday=5, hour=19)
        txn = system.book_wheels("C1", "E1", ["F1"])
        expected = 30.0 * 1.2 * (1 + 0.08)
        assert abs(txn.total_price - expected) < 0.01

    def test_weekday_morning_not_peak(self) -> None:
        """Reservation of a single wheel on a weekday morning must use regular pricing."""
        system = _make_event_pricing_system(weekday=2, hour=10)
        txn = system.book_wheels("C1", "E1", ["F1"])
        expected = 30.0 * (1 + 0.08)
        assert abs(txn.total_price - expected) < 0.01


class TestSeniorDiscountRules:

    def test_qualifying_age_student_receives_senior_rate(self) -> None:
        """A student who has reached the qualifying senior age must receive the reduced rate."""
        from pricing_service import PricingService
        svc = PricingService()

        class FakeEvent:
            class_session_id = "E_senior"
            def get_wheel_price(self, r): return 100.0

        class SeniorCustomer:
            age = 65
            is_returning_student = False

        class BaseCustomer:
            age = 30
            is_returning_student = False

        senior_result = svc.calculate(FakeEvent(), ["R1"], SeniorCustomer())
        base_result = svc.calculate(FakeEvent(), ["R2"], BaseCustomer())
        assert "senior" in senior_result.discounts_applied
        assert senior_result.total_price < base_result.total_price

    def test_senior_discount_exactly_10_percent(self) -> None:
        """Senior discount must be exactly 10% of the amount after other discounts."""
        from pricing_service import PricingService
        svc = PricingService()

        class FakeEvent:
            class_session_id = "E_senior2"
            def get_wheel_price(self, r): return 100.0

        class SeniorCustomer:
            age = 65
            is_returning_student = False

        class BaseCustomer:
            age = 30
            is_returning_student = False

        senior_result = svc.calculate(FakeEvent(), ["R1"], SeniorCustomer())
        base_result = svc.calculate(FakeEvent(), ["R2"], BaseCustomer())
        expected = base_result.subtotal * 0.10
        actual = senior_result.discount_amount
        assert abs(actual - expected) < 0.01, f"Expected {expected}, got {actual}"

    def test_senior_discount_applied_after_group(self) -> None:
        """Senior discount is calculated on the remaining amount after group discount."""
        from pricing_service import PricingService
        svc = PricingService()

        class FakeEvent:
            class_session_id = "E_senior3"
            def get_wheel_price(self, r): return 100.0

        class SeniorCustomer:
            age = 65
            is_returning_student = False

        result = svc.calculate(FakeEvent(), ["R1", "R2", "R3"], SeniorCustomer())
        assert "group" in result.discounts_applied
        assert "senior" in result.discounts_applied
        subtotal = 300.0
        group_discount = subtotal * 0.15
        remaining_after_group = subtotal - group_discount
        expected_senior = remaining_after_group * 0.10
        expected_total_discount = group_discount + expected_senior
        assert abs(result.discount_amount - expected_total_discount) < 0.01, (
            f"Expected total discount {expected_total_discount}, got {result.discount_amount}"
        )
