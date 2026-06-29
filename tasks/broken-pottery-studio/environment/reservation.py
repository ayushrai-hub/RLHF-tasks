from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from data import StatusEntry

VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending":                {"confirmed", "expired"},
    "confirmed":              {"cancellation_requested", "completed"},
    "cancellation_requested": {"cancelled"},
    "completed":              set(),
    "cancelled":              set(),
    "expired":                set(),
}

class InvalidStateTransition(Exception):
    pass

@dataclass
class Reservation:
    reservation_id: str
    student_id: str
    class_session_id: str
    wheels: list[str]
    total_price: float
    has_cancellation_coverage: bool = False
    non_refundable_amount: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    discounts_applied: list[str] = field(default_factory=list)
    status: str = "pending"
    _status_history: list[StatusEntry] = field(default_factory=list, repr=False)
    _payments: list[float] = field(default_factory=list, repr=False)

    def confirm(self) -> None:
        self._transition("confirmed")

    def complete(self) -> None:
        self._transition("completed")

    def request_cancellation(self) -> None:
        self._transition("cancellation_requested")

    def cancel(self) -> None:
        self._transition("cancelled")

    def expire(self) -> None:
        self._transition("expired")

    def is_cancellable(self) -> bool:
        return self.status in ("pending", "confirmed", "cancellation_requested")

    def is_modifiable(self) -> bool:
        return self.status in ("pending", "confirmed")

    def get_total_paid(self) -> float:
        return sum(self._payments)

    def get_resources(self) -> list[str]:
        return list(self.wheels)

    def get_status_history(self) -> list[StatusEntry]:
        return list(self._status_history)

    def record_payment(self, amount: float) -> None:
        self._payments.append(amount)

    def _transition(self, new_status: str, actor_id: str = "system") -> None:
        allowed = VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise InvalidStateTransition(
                f"Cannot transition Reservation from '{self.status}' to '{new_status}'"
            )
        self.status = new_status
        self._status_history.append(
            StatusEntry(status=new_status, transitioned_at=datetime.utcnow(), actor_id=actor_id)
        )
