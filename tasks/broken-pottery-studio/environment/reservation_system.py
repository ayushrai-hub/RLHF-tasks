from __future__ import annotations
import uuid
from data import BookingStats, CancellationResult
from reservation import Reservation
from pricing_service import PricingService
from availability_service import AvailabilityService
from refund_policy import RefundPolicy, RefundNotEligible
from waitlist_service import WaitlistService
from audit_log import AuditLog
from time_provider import TimeProvider

class ReservationError(Exception):
    def __init__(self, message: str, available_wheels: list[str] | None = None) -> None:
        super().__init__(message)
        self.available_wheels = available_wheels or []

class ReservationSystem:

    def __init__(self, time_provider: TimeProvider | None = None) -> None:
        self._time_provider = time_provider or TimeProvider()
        self.students: dict[str, object] = {}
        self.class_sessions: dict[str, object] = {}
        self.reservations: dict[str, Reservation] = {}
        self.pricing = PricingService()
        self.availability = AvailabilityService(time_fn=self._time_provider.now)
        self.refund_policy = RefundPolicy()
        self.waitlist = WaitlistService()
        self.audit = AuditLog()

    def add_student(self, student: object) -> None:
        customer_id = getattr(student, "student_id")
        self.students[customer_id] = student

    def add_class_session(self, class_session: object) -> None:
        event_id = getattr(class_session, "class_session_id")
        self.class_sessions[event_id] = class_session
        self.availability.register_event(event_id)

    def book_wheels(
        self,
        student_id: str,
        class_session_id: str,
        wheels: list[str],
    ) -> Reservation:
        student = self.students.get(student_id)
        if student is None:
            raise ReservationError("Invalid student")

        class_session = self.class_sessions.get(class_session_id)
        if class_session is None:
            raise ReservationError("Invalid class_session")

        if not getattr(student, "is_in_good_standing")():
            raise ReservationError("Student account is not in good standing")

        if not getattr(class_session, "is_bookable")():
            raise ReservationError("ClassSession is not available for booking")

        if not getattr(class_session, "is_eligible")(student):
            raise ReservationError("Student is not eligible for this class_session")

        if getattr(student, "has_reached_ticket_limit")(class_session_id, 8):
            raise ReservationError("Ticket limit reached for this class_session")

        available = self.availability.get_available_for_event(class_session)
        for wheel in wheels:
            if wheel not in available:
                raise ReservationError(
                    f"Wheel {wheel} is not available",
                    available_wheels=available,
                )

        price_info = self.pricing.calculate(class_session, wheels, student)
        reservation_id = f"BK{uuid.uuid4().hex[:6].upper()}"
        self.pricing.lock_price(reservation_id, price_info)

        hold_id = self.availability.hold(class_session, wheels, 300)
        self.availability.confirm_hold(hold_id)

        txn = Reservation(
            reservation_id=reservation_id,
            student_id=student_id,
            class_session_id=class_session_id,
            wheels=wheels,
            total_price=price_info.total_price,
            discounts_applied=price_info.discounts_applied,
        )
        txn.confirm()
        txn.record_payment(price_info.total_price)
        self.reservations[reservation_id] = txn
        getattr(student, "record_tickets")(class_session_id, len(wheels))

        self.audit.log("book_created", reservation_id, student_id, {
            "class_session_id": class_session_id,
            "wheels": wheels,
            "total_price": price_info.total_price,
        })
        return txn

    def cancel_reservation(self, reservation_id: str) -> CancellationResult:
        txn = self.reservations.get(reservation_id)
        if txn is None:
            raise ReservationError("Reservation not found")

        txn.request_cancellation()
        txn.cancel()

        self.availability.release_booking(txn.class_session_id, txn.wheels)

        try:
            refund_result = self.refund_policy.calculate(txn, self._time_provider.now())
            refund_amount = refund_result.refund_amount
        except RefundNotEligible:
            refund_amount = 0.0
        promoted = self.waitlist.promote(txn.class_session_id)

        self.audit.log("book_cancelled", reservation_id, "system", {
            "refund_amount": refund_amount,
            "waitlist_promoted": promoted,
        })
        return CancellationResult(
            transaction_id=reservation_id,
            status="cancelled",
            refund_amount=refund_amount,
            waitlist_promoted=promoted,
        )

    def add_to_waitlist(self, student_id: str, class_session_id: str) -> None:
        student = self.students.get(student_id)
        if student is None:
            raise ReservationError("Invalid student")
        tier = getattr(student, "loyalty_tier", "standard")
        self.waitlist.add(student_id, class_session_id, loyalty_tier=tier)

    def promote_from_waitlist(self, class_session_id: str) -> str | None:
        return self.waitlist.promote(class_session_id)

    def get_waitlist_position(self, student_id: str, class_session_id: str) -> int:
        return self.waitlist.get_position(student_id, class_session_id)

    def get_audit_log(self, entity_id: str) -> list:
        return self.audit.get_history(entity_id)

    def get_reservation(self, reservation_id: str) -> Reservation:
        txn = self.reservations.get(reservation_id)
        if txn is None:
            raise ReservationError("Reservation not found")
        return txn

    def get_reservation_stats(self, class_session_id: str) -> BookingStats:
        if class_session_id not in self.class_sessions:
            raise ReservationError("Invalid class_session")
        active = [
            t for t in self.reservations.values()
            if t.class_session_id == class_session_id and t.status in ("confirmed", "completed")
        ]
        cancelled = [
            t for t in self.reservations.values()
            if t.class_session_id == class_session_id and t.status == "cancelled"
        ]
        class_session = self.class_sessions[class_session_id]
        venue = getattr(class_session, "studio")
        total = venue.get_capacity()
        confirmed_count = len(active)
        return BookingStats(
            event_id=class_session_id,
            total_resources=total,
            confirmed_count=confirmed_count,
            available_count=total - confirmed_count,
            occupancy_rate=confirmed_count / total if total > 0 else 0.0,
            total_revenue=sum(t.get_total_paid() for t in active),
            cancellation_count=len(cancelled),
        )
