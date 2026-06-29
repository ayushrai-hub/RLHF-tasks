from __future__ import annotations
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable

@dataclass
class _CacheEntry:
    value: object
    expires_at: datetime | None

class Cache:
    """LRU cache with optional per-entry TTL."""

    def __init__(self, capacity: int = 256, time_fn: Callable[[], datetime] | None = None) -> None:
        self._capacity = capacity
        self._store: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._time_fn = time_fn or datetime.utcnow

    def get(self, key: str) -> object | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at is not None and self._time_fn() > entry.expires_at:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return entry.value

    def set(self, key: str, value: object, ttl_seconds: int | None = None) -> None:
        expires_at = (
            self._time_fn() + timedelta(seconds=ttl_seconds)
            if ttl_seconds is not None
            else None
        )
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = _CacheEntry(value=value, expires_at=expires_at)
        if len(self._store) > self._capacity:
            self._store.popitem(last=False)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def invalidate_pattern(self, pattern: str) -> None:
        import fnmatch
        keys = [k for k in self._store if fnmatch.fnmatch(k, pattern)]
        for k in keys:
            del self._store[k]

    def get_or_set(
        self,
        key: str,
        loader_fn: Callable[[], object],
        ttl_seconds: int | None = None,
    ) -> object:
        value = self.get(key)
        if value is None:
            value = loader_fn()
            self.set(key, value, ttl_seconds)
        return value
