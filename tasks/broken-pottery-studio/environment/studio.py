from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from data import Address, Section

class WheelNotFound(Exception):
    pass

class SectionNotFound(Exception):
    pass

@dataclass
class Studio:
    studio_id: str
    name: str
    address: Address
    sections: list[Section]
    max_occupancy: int
    _blocked: set[str] = field(default_factory=set, repr=False)

    def get_capacity(self) -> int:
        return sum(s.capacity for s in self.sections)

    def get_available_resources(self, section: str | None = None) -> list[str]:
        if section is not None:
            target = self._get_section(section)
            return list(target.resource_ids)
        return [
            r
            for s in self.sections
            for r in s.resource_ids

        ]

    def is_at_capacity(self, current_occupancy: int) -> bool:
        return current_occupancy >= self.max_occupancy

    def contains(self, resource_id: str) -> bool:
        return any(resource_id in s.resource_ids for s in self.sections)

    def block(self, resource_id: str) -> None:
        if not self.contains(resource_id):
            raise WheelNotFound(f"Wheel '{resource_id}' not in studio")
        self._blocked.add(resource_id)

    def unblock(self, resource_id: str) -> None:
        if not self.contains(resource_id):
            raise WheelNotFound(f"Wheel '{resource_id}' not in studio")
        self._blocked.discard(resource_id)

    def _get_section(self, name: str) -> Section:
        for s in self.sections:
            if s.name == name:
                return s
        raise SectionNotFound(f"Section '{name}' not found")

@dataclass
class ClassSession:
    class_session_id: str
    studio: Studio
    time: datetime
    status: str = "scheduled"
    restrictions: dict[str, object] = field(default_factory=dict)

    def get_wheel_price(self, resource_id: str) -> float:
        if not self.studio.contains(resource_id):
            raise WheelNotFound(f"Wheel '{resource_id}' not in venue")
        row = resource_id[0]
        base_price = self._get_base_price(row)
        if self._is_peak_time():
            base_price *= 1.20
        return base_price

    def _get_base_price(self, row: str) -> float:
        if row in ("A", "B"):
            return 95.0
        if row in ("C", "D", "E"):
            return 60.0
        return 30.0

    def _is_peak_time(self) -> bool:
        is_weekend = self.time.weekday() in (5, 6)
        is_evening = 18 <= self.time.hour < 22
        return is_weekend or is_evening

    def is_bookable(self) -> bool:
        from datetime import timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return self.status == "scheduled" and self.time > now

    def is_eligible(self, customer: object) -> bool:
        min_age = self.restrictions.get("min_age")
        if min_age is not None:
            customer_age = getattr(customer, "age", None)
            if customer_age is None or customer_age < int(min_age):
                return False
        return True

    def is_sold_out(self, current_occupancy: int) -> bool:
        return self.studio.is_at_capacity(current_occupancy)

    def cancel(self) -> None:
        if self.status == "cancelled":
            raise ValueError("ClassSession is already cancelled")
        self.status = "cancelled"
