from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
import uuid

class ResourceUnavailable(Exception):
    pass

class HoldNotFound(Exception):
    pass

class HoldExpired(Exception):
    pass

@dataclass
class _Hold:
    hold_id: str
    event_id: str
    resource_ids: frozenset[str]
    owner_id: str
    expires_at: datetime
    confirmed: bool = False

class AvailabilityService:

    def __init__(self, time_fn: object = None) -> None:
        self._booked: dict[str, set[str]] = {}
        self._holds: dict[str, _Hold] = {}
        self._time_fn = time_fn or datetime.utcnow

    def register_event(self, event_id: str) -> None:
        self._booked.setdefault(event_id, set())

    def get_available(self, event_id: str, section: object = None) -> list[str]:
        raise NotImplementedError("Requires event reference — use TransactionService")

    def get_available_for_event(self, event: object, section: str | None = None) -> list[str]:
        event_id: str = getattr(event, "class_session_id")
        venue = getattr(event, "studio")
        all_resources = venue.get_available_resources(section)
        booked = self._booked.get(event_id, set())
        held = self._get_active_held_ids(event_id)
        return [r for r in all_resources if r not in booked and r not in held]

    def is_available(self, event: object, resource_id: str) -> bool:
        return resource_id in self.get_available_for_event(event)

    def hold(self, event: object, resource_ids: list[str], ttl_seconds: int) -> str:
        event_id: str = getattr(event, "class_session_id")
        available = set(self.get_available_for_event(event))
        unavailable = [r for r in resource_ids if r not in available]
        if unavailable:
            raise ResourceUnavailable(f"Wheels not available: {unavailable}")
        hold_id = uuid.uuid4().hex
        now = self._time_fn()
        from datetime import timedelta
        self._holds[hold_id] = _Hold(
            hold_id=hold_id,
            event_id=event_id,
            resource_ids=frozenset(resource_ids),
            owner_id="",
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        return hold_id

    def release_hold(self, hold_id: str) -> None:
        if hold_id not in self._holds:
            raise HoldNotFound(f"Hold '{hold_id}' not found")
        del self._holds[hold_id]

    def confirm_hold(self, hold_id: str) -> None:
        hold = self._holds.get(hold_id)
        if hold is None:
            raise HoldNotFound(f"Hold '{hold_id}' not found")
        if self._time_fn() > hold.expires_at:
            raise HoldExpired(f"Hold '{hold_id}' has expired")
        for resource_id in hold.resource_ids:
            self._booked.setdefault(hold.event_id, set()).add(resource_id)
        del self._holds[hold_id]

    def release_booking(self, event_id: str, resource_ids: list[str]) -> None:
        booked = self._booked.get(event_id, set())
        for r in resource_ids:
            booked.discard(r)

    def _get_active_held_ids(self, event_id: str) -> set[str]:
        self._time_fn()
        return {
            r
            for h in self._holds.values()
            if h.event_id == event_id and not h.confirmed
            for r in h.resource_ids
        }
