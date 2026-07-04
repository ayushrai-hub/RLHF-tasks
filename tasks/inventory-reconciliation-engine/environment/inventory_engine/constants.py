from __future__ import annotations

ALLOWED_FIELDS = frozenset(
    {
        "event_id",
        "product_id",
        "operation",
        "quantity",
        "event_time",
        "supplier_id",
        "version",
        "target_event_id",
    }
)

MUTATING_OPS = frozenset({"ADD", "REMOVE", "SET", "DELETE", "RESTORE", "ROLLBACK"})
QUANTITY_OPS = frozenset({"ADD", "REMOVE", "SET"})

REJECTION_RANKS = {
    "missing_required": 1,
    "unexpected_fields": 2,
    "invalid_types": 3,
    "invalid_event_id": 4,
    "invalid_product_id": 5,
    "invalid_supplier_id": 6,
    "invalid_operation": 7,
    "invalid_event_time": 8,
    "invalid_version": 9,
    "invalid_quantity": 10,
    "missing_target": 11,
    "invalid_target": 12,
    "duplicate_event_id": 13,
    "stale_version": 14,
    "product_deleted": 15,
    "product_not_deleted": 16,
    "restore_supplier_mismatch": 17,
    "negative_inventory": 18,
    "supplier_conflict": 19,
    "rollback_product_deleted": 20,
    "rollback_self": 21,
    "rollback_supplier_mismatch": 22,
    "rollback_cross_product": 23,
    "rollback_target_missing": 24,
    "rollback_target_not_applied": 25,
    "rollback_already_reversed": 26,
    "rollback_invalid_target": 27,
}

GENERATED_FROM = "inventory-reconcile-v1"

EVENT_ID_RE = r"^EV-[A-Z0-9]{6}$"
PRODUCT_ID_RE = r"^PRD-[A-Z0-9]{4,8}$"
SUPPLIER_ID_RE = r"^SUP-[A-Z0-9]{3,6}$"
