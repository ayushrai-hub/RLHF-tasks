#!/bin/bash
set -euo pipefail

# Fix availability: assign now and filter expired holds in _get_active_held_ids
sed -i 's/        self\._time_fn()$/        now = self._time_fn()/' /app/availability_service.py
sed -i 's/if h\.event_id == event_id and not h\.confirmed$/if h.event_id == event_id and not h.confirmed and h.expires_at > now/' /app/availability_service.py

# Fix cache: distinguish None value from cache miss in get_or_set
sed -i 's/        value = self\.get(key)$/        value = self.get(key)\n        if value is None and key in self._store:\n            return value/' /app/cache.py
sed -i 's/        if value is None:$/        if value is None and key not in self._store:/' /app/cache.py
