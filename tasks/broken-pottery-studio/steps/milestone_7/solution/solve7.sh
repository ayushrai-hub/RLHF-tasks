#!/bin/bash
set -euo pipefail

# Fix refund: check cancellation coverage flag
sed -i 's/        return True.*/        return bool(getattr(transaction, "has_cancellation_coverage", False))/' /app/refund_policy.py

# Fix refund: prorated ratio is cancelled/total, not total/cancelled
sed -i 's/        ratio = len(all_resources) \/ len(resources_cancelled).*/        ratio = len(resources_cancelled) \/ len(all_resources)/' /app/refund_policy.py

# Fix customer: record_tickets must accumulate across purchases
sed -i 's/        self\.ticket_history\[event_id\] = count$/        self.ticket_history[event_id] = self.ticket_history.get(event_id, 0) + count/' /app/student.py

# Fix customer: ticket limit check must use >= not >
sed -i 's/        return self\.ticket_history\.get(event_id, 0) > limit$/        return self.ticket_history.get(event_id, 0) >= limit/' /app/student.py
