from __future__ import annotations

import re

from inventory_engine.constants import (
    ALLOWED_FIELDS,
    EVENT_ID_RE,
    PRODUCT_ID_RE,
    QUANTITY_OPS,
    REJECTION_RANKS,
)
from inventory_engine.loader import parse_event_time


def normalize_id(raw: str) -> str:
    return raw.strip().upper()


def canonical_payload(obj: dict) -> dict:
    out: dict = {}
    for key in sorted(obj.keys()):
        if key not in ALLOWED_FIELDS:
            continue
        value = obj[key]
        if value is None:
            out[key] = None
        elif key in {"event_id", "product_id", "supplier_id", "target_event_id"}:
            out[key] = normalize_id(str(value))
        elif key == "operation":
            out[key] = str(value).strip().upper()
        else:
            out[key] = value
    return out


def validate_event(obj: dict) -> tuple[dict | None, dict | None]:
    """Return (normalized_event, rejection) — broken: incomplete priority chain."""
    required = ("event_id", "product_id", "operation", "event_time", "supplier_id", "version")
    for req_field in required:
        if req_field not in obj or obj[req_field] is None:
            return None, _reject(str(obj.get("event_id", "")), str(obj.get("product_id", "")), "missing_required")

    extra = set(obj.keys()) - ALLOWED_FIELDS
    if extra:
        return None, _reject(str(obj["event_id"]), str(obj["product_id"]), "unexpected_fields")

    event_id = normalize_id(str(obj["event_id"]))
    product_id = normalize_id(str(obj["product_id"]))
    supplier_id = normalize_id(str(obj["supplier_id"]))
    operation = str(obj["operation"]).strip().upper()

    if not re.fullmatch(EVENT_ID_RE, event_id):
        return None, _reject(event_id, product_id, "invalid_event_id")
    if not re.fullmatch(PRODUCT_ID_RE, product_id):
        return None, _reject(event_id, product_id, "invalid_product_id")

    if operation not in {"ADD", "REMOVE", "SET", "DELETE", "RESTORE", "ROLLBACK"}:
        return None, _reject(event_id, product_id, "invalid_operation")

    try:
        event_time = parse_event_time(str(obj["event_time"]))
    except ValueError:
        return None, _reject(event_id, product_id, "invalid_event_time")

    version = obj["version"]
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        return None, _reject(event_id, product_id, "invalid_version")

    normalized = {
        "event_id": event_id,
        "product_id": product_id,
        "operation": operation,
        "event_time": event_time,
        "supplier_id": supplier_id,
        "version": version,
    }

    if operation in QUANTITY_OPS:
        qty = obj.get("quantity")
        if qty is None or isinstance(qty, bool) or not isinstance(qty, int):
            return None, _reject(event_id, product_id, "invalid_quantity")
        normalized["quantity"] = qty
    elif "quantity" in obj and obj["quantity"] is not None:
        return None, _reject(event_id, product_id, "invalid_quantity")

    if operation == "ROLLBACK":
        target = obj.get("target_event_id")
        if target is None:
            return None, _reject(event_id, product_id, "missing_target")
        normalized["target_event_id"] = normalize_id(str(target))

    return normalized, None


def _reject(event_id: str, product_id: str, reason: str) -> dict:
    return {
        "event_id": event_id,
        "product_id": product_id,
        "reason": reason,
        "priority_rank": REJECTION_RANKS[reason],
    }
