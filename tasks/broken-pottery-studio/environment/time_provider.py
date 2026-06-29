from __future__ import annotations
from datetime import datetime

class TimeProvider:
    """Injectable time source. Subclass in tests to control time."""

    def now(self) -> datetime:
        return datetime.utcnow()
