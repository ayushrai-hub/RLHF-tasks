from __future__ import annotations
from dataclasses import dataclass, field
from data import Address

LOYALTY_TIERS: list[str] = ['standard', 'silver', 'gold', 'platinum']
_TIER_RANK: dict[str, int] = {tier: i for i, tier in enumerate(LOYALTY_TIERS)}

@dataclass
class Student:
    student_id: str
    name: str
    age: int
    address: Address
    is_returning_student: bool = False
    loyalty_tier: str = "standard"
    status: str = "active"
    ticket_history: dict[str, int] = field(default_factory=dict)

    def is_eligible_for(self, discount_type: str) -> bool:
        if discount_type == "returning_student":
            return _TIER_RANK.get(self.loyalty_tier, 0) > 0
        return False

    def is_in_good_standing(self) -> bool:
        return self.status == "active"

    def has_reached_ticket_limit(self, event_id: str, limit: int) -> bool:
        return self.ticket_history.get(event_id, 0) > limit

    def get_loyalty_tier(self) -> str:
        return self.loyalty_tier

    def record_tickets(self, event_id: str, count: int) -> None:
        self.ticket_history[event_id] = count
