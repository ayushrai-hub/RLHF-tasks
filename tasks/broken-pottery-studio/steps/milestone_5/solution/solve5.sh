#!/bin/bash
set -euo pipefail

# Fix waitlist: negate tier rank so higher tier sorts first
sed -i 's/queue\.sort(key=lambda e: (_TIER_RANK\.get(e\.loyalty_tier, 0), e\.joined_at)).*/queue.sort(key=lambda e: (-_TIER_RANK.get(e.loyalty_tier, 0), e.joined_at))/' /app/waitlist_service.py

# Fix waitlist: get_position returns 1-based index
sed -i 's/                return i.*/                return i + 1/' /app/waitlist_service.py

# Fix transaction: pending status must not be reported as cancellable
sed -i 's/        return self\.status in ("pending", "confirmed", "cancellation_requested")$/        return self.status in ("confirmed", "cancellation_requested")/' /app/reservation.py
