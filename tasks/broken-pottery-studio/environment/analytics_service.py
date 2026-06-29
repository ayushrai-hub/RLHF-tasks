from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ServiceEvent:
    event_type: str
    entity_id: str
    recorded_at: datetime
    metadata: dict = field(default_factory=dict)


class AnalyticsService:
    def __init__(self) -> None:
        self._events: list[ServiceEvent] = []

    def record(self, event_type: str, entity_id: str, metadata: dict | None = None) -> None:
        self._events.append(ServiceEvent(
            event_type=event_type,
            entity_id=entity_id,
            recorded_at=datetime.utcnow(),
            metadata=metadata or {},
        ))

    def count(self, event_type: str) -> int:
        return sum(1 for e in self._events if e.event_type == event_type)

    def get_by_entity(self, entity_id: str) -> list[ServiceEvent]:
        return [e for e in self._events if e.entity_id == entity_id]
