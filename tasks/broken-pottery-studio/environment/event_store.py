from __future__ import annotations
import copy
import uuid
from dataclasses import dataclass
from datetime import datetime

@dataclass
class EventEntry:
    entry_id: str
    stream_id: str
    event_type: str
    payload: dict
    sequence_number: int
    timestamp: datetime

class EventStore:

    def __init__(self) -> None:
        self._streams: dict[str, list[EventEntry]] = {}
        self._snapshots: dict[str, object] = {}
        self._sequence: int = 0

    def append(self, stream_id: str, event_type: str, payload: dict) -> EventEntry:
        self._sequence += 1
        entry = EventEntry(
            entry_id=uuid.uuid4().hex,
            stream_id=stream_id,
            event_type=event_type,
            payload=copy.deepcopy(payload),
            sequence_number=self._sequence,
            timestamp=datetime.utcnow(),
        )
        self._streams.setdefault(stream_id, []).append(entry)
        return entry

    def read(self, stream_id: str) -> list[EventEntry]:
        return list(self._streams.get(stream_id, []))

    def read_from(self, stream_id: str, sequence_number: int) -> list[EventEntry]:
        return [e for e in self._streams.get(stream_id, []) if e.sequence_number >= sequence_number]

    def snapshot(self, stream_id: str, state: object) -> None:
        self._snapshots[stream_id] = copy.deepcopy(state)

    def get_snapshot(self, stream_id: str) -> object | None:
        return self._snapshots.get(stream_id)
