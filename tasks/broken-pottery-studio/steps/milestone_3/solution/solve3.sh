#!/bin/bash
set -euo pipefail

# Fix audit: add missing copy import
sed -i 's/^import uuid$/import copy\nimport uuid/' /app/audit_log.py

# Fix audit: deep-copy payload on write
sed -i 's/            payload=payload,.*/            payload=copy.deepcopy(payload),/' /app/audit_log.py

# Fix audit: filter get_history by entity_id
sed -i 's/        return list(self\._entries).*/        return [e for e in self._entries if e.entity_id == entity_id]/' /app/audit_log.py

# Fix audit: return deep copies from get_history so callers cannot mutate stored entries
sed -i 's/        return \[e for e in self\._entries if e\.entity_id == entity_id\]$/        return [copy.deepcopy(e) for e in self._entries if e.entity_id == entity_id]/' /app/audit_log.py

# Fix event-store: deep-copy entries on read so callers cannot mutate stored events
sed -i 's/        return list(self\._streams\.get(stream_id, \[\]))$/        return [copy.deepcopy(e) for e in self._streams.get(stream_id, [])]/' /app/event_store.py
sed -i 's/        return \[e for e in self\._streams\.get(stream_id, \[\]) if e\.sequence_number >= sequence_number\]$/        return [copy.deepcopy(e) for e in self._streams.get(stream_id, []) if e.sequence_number >= sequence_number]/' /app/event_store.py
