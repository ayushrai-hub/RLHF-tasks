from __future__ import annotations

from dataclasses import dataclass, field

from inventory_engine.validate import canonical_payload


@dataclass
class ProductState:
    quantity: int = 0
    deleted: bool = False
    last_event_id: str = ""
    last_event_time: str = ""


@dataclass
class EngineState:
    products: dict[str, ProductState] = field(default_factory=dict)
    seen_event_ids: dict[str, dict] = field(default_factory=dict)
    applied: dict[str, dict] = field(default_factory=dict)
    rejected_ids: set[str] = field(default_factory=set)
    rolled_back: set[str] = field(default_factory=set)
    version_highwater: dict[tuple[str, str, str], int] = field(default_factory=dict)
    set_at_time: dict[tuple[str, str], str] = field(default_factory=dict)
    set_prev_qty: dict[str, int] = field(default_factory=dict)


class InventoryEngine:
    """Replay supplier events into warehouse product state."""

    def __init__(self) -> None:
        self.state = EngineState()
        self.applied_count = 0
        self.rejected_count = 0
        self.skipped_idempotent_count = 0
        self.rejections: list[dict] = []

    def process(self, events: list[dict]) -> None:
        for event in events:
            self._apply_one(event)

    def _apply_one(self, event: dict) -> None:
        from inventory_engine.validate import validate_event

        normalized, rejection = validate_event(event["payload"])
        if rejection is not None:
            self.rejections.append(rejection)
            self.rejected_count += 1
            eid = rejection["event_id"]
            if eid:
                self.state.rejected_ids.add(eid)
            return

        assert normalized is not None
        event_id = normalized["event_id"]
        product_id = normalized["product_id"]
        operation = normalized["operation"]

        canon = canonical_payload(event["payload"])
        if event_id in self.state.seen_event_ids:
            if self.state.seen_event_ids[event_id] != canon:
                self._reject(event_id, product_id, "duplicate_event_id")
            else:
                self.skipped_idempotent_count += 1
            return
        self.state.seen_event_ids[event_id] = canon

        product = self.state.products.setdefault(product_id, ProductState())

        if operation in {"ADD", "REMOVE", "SET"} and product.deleted:
            self._reject(event_id, product_id, "product_deleted")
            return

        if operation == "RESTORE" and not product.deleted:
            self._reject(event_id, product_id, "product_not_deleted")
            return

        if operation in {"ADD", "REMOVE", "SET", "DELETE", "RESTORE"}:
            key = (product_id, normalized["supplier_id"], operation)
            prev = self.state.version_highwater.get(key, 0)
            if normalized["version"] <= prev:
                self._reject(event_id, product_id, "stale_version")
                return

        if operation == "SET":
            conflict_key = (product_id, normalized["event_time"].strftime("%Y-%m-%dT%H:%M:%SZ"))
            existing = self.state.set_at_time.get(conflict_key)
            if existing and existing != normalized["supplier_id"]:
                pass
            self.state.set_at_time[conflict_key] = normalized["supplier_id"]

        if operation == "ADD":
            product.quantity += normalized["quantity"]
        elif operation == "REMOVE":
            product.quantity -= normalized["quantity"]
            if product.quantity < 0:
                product.quantity += normalized["quantity"]
                self._reject(event_id, product_id, "negative_inventory")
                return
        elif operation == "SET":
            product.quantity = normalized["quantity"]
        elif operation == "DELETE":
            product.deleted = True
        elif operation == "RESTORE":
            product.deleted = False
        elif operation == "ROLLBACK":
            target_id = normalized["target_event_id"]
            if target_id == event_id:
                self._reject(event_id, product_id, "rollback_self")
                return
            target = self.state.applied.get(target_id)
            if target is None:
                reason = "rollback_target_not_applied" if target_id in self.state.rejected_ids else "rollback_target_missing"
                self._reject(event_id, product_id, reason)
                return
            if target_id in self.state.rolled_back:
                self._reject(event_id, product_id, "rollback_already_reversed")
                return
            top = target["operation"]
            if top in {"DELETE", "RESTORE", "ROLLBACK"}:
                self._reject(event_id, product_id, "rollback_invalid_target")
                return
            product.quantity = self.state.set_prev_qty.get(target_id, product.quantity)
            self.state.rolled_back.add(target_id)

        product.last_event_id = event_id
        product.last_event_time = normalized["event_time"].strftime("%Y-%m-%dT%H:%M:%SZ")
        self.state.applied[event_id] = normalized
        if operation in {"ADD", "REMOVE", "SET", "DELETE", "RESTORE"}:
            key = (product_id, normalized["supplier_id"], operation)
            self.state.version_highwater[key] = normalized["version"]
        self.applied_count += 1

    def _reject(self, event_id: str, product_id: str, reason: str) -> None:
        from inventory_engine.constants import REJECTION_RANKS

        self.rejections.append(
            {
                "event_id": event_id,
                "product_id": product_id,
                "reason": reason,
                "priority_rank": REJECTION_RANKS[reason],
            }
        )
        self.rejected_count += 1
        if event_id:
            self.state.rejected_ids.add(event_id)

    def inventory_rows(self) -> list[dict]:
        rows: list[dict] = []
        for product_id in sorted(self.state.products.keys()):
            product = self.state.products[product_id]
            if product.deleted:
                continue
            rows.append(
                {
                    "product_id": product_id,
                    "quantity": product.quantity,
                    "last_event_id": product.last_event_id,
                    "last_event_time": product.last_event_time,
                }
            )
        return rows
