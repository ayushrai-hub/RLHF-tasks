from __future__ import annotations
import uuid
from datetime import datetime
from data import AuditEntry

class AuditLog:

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def log(
        self,
        event_type: str,
        entity_id: str,
        actor_id: str,
        payload: dict,
    ) -> AuditEntry:
        entry = AuditEntry(
            entry_id=uuid.uuid4().hex,
            event_type=event_type,
            entity_id=entity_id,
            actor_id=actor_id,
            payload=payload,
            timestamp=datetime.utcnow(),
        )
        self._entries.append(entry)
        return entry

    def get_history(self, entity_id: str) -> list[AuditEntry]:
        return list(self._entries)

    def get_by_actor(self, actor_id: str) -> list[AuditEntry]:
        return [e for e in self._entries if e.actor_id == actor_id]

    def get_by_type(self, event_type: str) -> list[AuditEntry]:
        return [e for e in self._entries if e.event_type == event_type]
