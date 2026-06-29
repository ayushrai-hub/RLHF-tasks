from __future__ import annotations
import sys
sys.path.append('/app')
from datetime import datetime
from data import Address, Section
from studio import Studio, ClassSession
from student import Student
from reservation_system import ReservationSystem


def _make_pricing_system() -> ReservationSystem:
    sections = [
        Section("VIP", 4, [f"A{n}" for n in range(1, 5)]),
        Section("Regular", 6, [f"F{n}" for n in range(1, 7)]),
    ]
    venue = Studio(
        studio_id="V1", name="Test", address=Address("1 Main", "City", "ST", "00000"),
        sections=sections, max_occupancy=10,
    )
    event = ClassSession(class_session_id="E1", studio=venue, time=datetime(2030, 6, 3, 14, 0))
    standard = Student(student_id="C1", name="Standard", age=30,
                       address=Address("1 Main", "City", "ST", "00000"),
                       is_returning_student=False, loyalty_tier="standard")
    loyal = Student(student_id="C2", name="Loyal", age=30,
                    address=Address("1 Main", "City", "ST", "00000"),
                    is_returning_student=True, loyalty_tier="gold")
    system = ReservationSystem()
    system.add_class_session(event)
    system.add_student(standard)
    system.add_student(loyal)
    return system


class TestSessionPricingRules:

    def test_standard_student_group_session_invoice_total(self) -> None:
        """
        A standard student booking three or more wheels receives a group savings
        percentage applied to the session subtotal. The studio fee is calculated on
        the post-savings amount, not the original.
        """
        system = _make_pricing_system()
        txn = system.book_wheels("C1", "E1", ["F1", "F2", "F3"])
        subtotal = 30.0 * 3
        group_savings = subtotal * 0.15
        expected_total = (subtotal - group_savings) * (1 + 0.08)
        assert abs(txn.total_price - expected_total) < 0.01

    def test_returning_student_group_session_invoice_total(self) -> None:
        """
        A returning student booking multiple wheels receives both the group savings and
        the loyalty savings, each computed independently against the original session
        subtotal. The studio fee applies to the final post-discount amount.
        """
        system = _make_pricing_system()
        txn = system.book_wheels("C2", "E1", ["F4", "F5", "F6"])
        subtotal = 30.0 * 3
        group_savings = subtotal * 0.15
        loyalty_savings = subtotal * 0.10
        expected_total = (subtotal - group_savings - loyalty_savings) * (1 + 0.08)
        assert abs(txn.total_price - expected_total) < 0.01
