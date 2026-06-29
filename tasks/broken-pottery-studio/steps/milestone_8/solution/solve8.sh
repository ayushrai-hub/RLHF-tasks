#!/bin/bash
set -euo pipefail

# Fix circuit-breaker: reset _suspended_at when re-suspending from PROBING state
sed -i '/if self\._state == PROBING:/{n;s/            self\._state = SUSPENDED$/            self._state = SUSPENDED\n            self._suspended_at = self._time_fn()/}' /app/circuit_breaker.py

# Fix pagination: restore math import and use ceiling division for total_pages
sed -i 's/^from dataclasses import dataclass$/import math\nfrom dataclasses import dataclass/' /app/pagination.py
sed -i 's/total_pages = total_count \/\/ page_size if page_size > 0 else 1/total_pages = math.ceil(total_count \/ page_size) if page_size > 0 else 1/' /app/pagination.py

# Fix rate-limiter: cap tokens at capacity during refill
sed -i 's/        self._tokens += elapsed \* self.refill_rate$/        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)/' /app/rate_limiter.py

# Fix retry: use exponential backoff instead of fixed delay
sed -i 's/                    self._sleep(self.base_delay)$/                    self._sleep(self.base_delay * (2 ** (attempt - 1)))/' /app/retry.py
