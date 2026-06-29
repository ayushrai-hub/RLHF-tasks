#!/bin/bash
set -euo pipefail

# Fix lock: clear debounce entries for both owner and all waiters on release
sed -i 's/        del self\._leases\[resource_id\]$/        self._debounce = {k: v for k, v in self._debounce.items() if k[0] != resource_id}\n        del self._leases[resource_id]/' /app/lock_manager.py

# Fix venue: filter blocked resources in section path
sed -i 's/            return list(target\.resource_ids)$/            return [r for r in target.resource_ids if r not in self._blocked]/' /app/studio.py

# Fix venue: replace blank line after 'for r in s.resource_ids' with the filter condition
sed -i '/            for r in s\.resource_ids$/{n;s/^$/            if r not in self._blocked/}' /app/studio.py
