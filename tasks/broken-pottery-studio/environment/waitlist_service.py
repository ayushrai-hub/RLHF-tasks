from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from data import WaitlistEntry

LOYALTY_TIERS: list[str] = ['standard', 'silver', 'gold', 'platinum']
_TIER_RANK: dict[str, int] = {tier: i for i, tier in enumerate(LOYALTY_TIERS)}

class AlreadyOnWaitlist(Exception):
    pass

class NotOnWaitlist(Exception):
    pass

@dataclass
class _Entry:
    customer_id: str
    event_id: str
    loyalty_tier: str
    joined_at: datetime

class WaitlistService:

    def __init__(self) -> None:
        self._queues: dict[str, list[_Entry]] = {}

    def add(self, customer_id: str, event_id: str, loyalty_tier: str = "standard") -> int:
        queue = self._queues.setdefault(event_id, [])
        if any(e.customer_id == customer_id for e in queue):
            raise AlreadyOnWaitlist(f"Student '{customer_id}' already on waitlist for '{event_id}'")
        entry = _Entry(
            customer_id=customer_id,
            event_id=event_id,
            loyalty_tier=loyalty_tier,
            joined_at=datetime.utcnow(),
        )
        queue.append(entry)
        self._sort(event_id)
        return self.get_position(customer_id, event_id)

    def remove(self, customer_id: str, event_id: str) -> None:
        queue = self._queues.get(event_id, [])
        for i, e in enumerate(queue):
            if e.customer_id == customer_id:
                queue.pop(i)
                return
        raise NotOnWaitlist(f"Student '{customer_id}' not on waitlist for '{event_id}'")

    def promote(self, event_id: str) -> str | None:
        queue = self._queues.get(event_id, [])
        if not queue:
            return None
        entry = queue.pop(0)
        return entry.customer_id

    def get_position(self, customer_id: str, event_id: str) -> int:
        queue = self._queues.get(event_id, [])
        for i, e in enumerate(queue):
            if e.customer_id == customer_id:
                return i
        raise NotOnWaitlist(f"Student '{customer_id}' not on waitlist for '{event_id}'")

    def list(self, event_id: str) -> list[WaitlistEntry]:
        return [
            WaitlistEntry(
                customer_id=e.customer_id,
                event_id=e.event_id,
                position=i + 1,
                loyalty_tier=e.loyalty_tier,
                joined_at=e.joined_at,
            )
            for i, e in enumerate(self._queues.get(event_id, []))
        ]

    def update_tier(self, customer_id: str, event_id: str, new_tier: str) -> None:
        queue = self._queues.get(event_id, [])
        for e in queue:
            if e.customer_id == customer_id:
                e.loyalty_tier = new_tier
                self._sort(event_id)
                return
        raise NotOnWaitlist(f"Student '{customer_id}' not on waitlist for '{event_id}'")

    def _sort(self, event_id: str) -> None:
        queue = self._queues.get(event_id, [])
        queue.sort(key=lambda e: (_TIER_RANK.get(e.loyalty_tier, 0), e.joined_at))
