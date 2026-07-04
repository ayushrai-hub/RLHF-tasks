"""Structured reconciliation errors."""

from inventory_engine.constants import REJECTION_RANKS


def rejection_row(event_id: str, product_id: str, reason: str) -> dict:
    return {
        "event_id": event_id,
        "product_id": product_id,
        "reason": reason,
        "priority_rank": REJECTION_RANKS[reason],
    }
