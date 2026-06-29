from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class RawEvent:
    line_index: int
    payload: dict


def load_events(path: Path) -> tuple[list[RawEvent], int, int]:
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    parsed: list[RawEvent] = []
    malformed = 0
    for index, line in enumerate(lines):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            continue
        if not isinstance(payload, dict):
            malformed += 1
            continue
        parsed.append(RawEvent(line_index=index, payload=payload))
    return parsed, len(lines), malformed


def parse_event_time(raw: str) -> datetime:
    if not raw.endswith("Z"):
        raise ValueError("missing Z suffix")
    base = raw[:-1]
    dt = datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
    return dt.replace(tzinfo=timezone.utc)
