# Reconciliation rules

## Validation priority

Evaluate each parsed event in sorted `(event_time, event_id, source_line_index)` order. Stop at the first matching rejection reason below. Rejection rows contain `event_id`, `product_id`, `reason`, and `priority_rank`. Use the exact `reason` strings and ranks from `/app/inventory_engine/constants.py`.

| Rank | reason | When |
|------|--------|------|
| 1 | `missing_required` | Required key absent or JSON `null`. |
| 2 | `unexpected_fields` | Any key outside the allowed set. |
| 3 | `invalid_types` | Wrong JSON type. |
| 4 | `invalid_event_id` | Bad `event_id` format after normalization. |
| 5 | `invalid_product_id` | Bad `product_id` format. |
| 6 | `invalid_supplier_id` | Bad `supplier_id` format. |
| 7 | `invalid_operation` | Not one of the six operations. |
| 8 | `invalid_event_time` | Does not parse as required UTC format. |
| 9 | `invalid_version` | Not an integer `>= 1`. |
| 10 | `invalid_quantity` | Quantity presence or bounds wrong for the operation. |
| 11 | `missing_target` | `ROLLBACK` without `target_event_id`. |
| 12 | `invalid_target` | Bad `target_event_id` format. |
| 13 | `duplicate_event_id` | Same `event_id` seen earlier with a different canonical payload. |
| 14 | `stale_version` | For `(product_id, supplier_id)`, an applied mutating event already has version `>=` this event's version. Applies to `ADD`, `REMOVE`, `SET`, `DELETE`, `RESTORE`, and `ROLLBACK`. |
| 15 | `product_deleted` | `ADD`, `REMOVE`, or `SET` while the product is deleted. |
| 16 | `product_not_deleted` | `RESTORE` when the product is not deleted. |
| 17 | `restore_supplier_mismatch` | `RESTORE` from a supplier other than the one that applied the active `DELETE`. |
| 18 | `negative_inventory` | `REMOVE` would make on-hand quantity negative. |
| 19 | `supplier_conflict` | Another supplier's `SET` for the same `product_id` at the same `event_time` was already applied. |
| 20 | `rollback_product_deleted` | `ROLLBACK` while the product is deleted. |
| 21 | `rollback_self` | `target_event_id` equals this event's `event_id`. |
| 22 | `rollback_supplier_mismatch` | Target event's `supplier_id` differs from this `ROLLBACK`'s `supplier_id`. |
| 23 | `rollback_cross_product` | Target event belongs to a different `product_id`. |
| 24 | `rollback_target_missing` | Target id was never applied. |
| 25 | `rollback_target_not_applied` | Target id exists only among rejected events. |
| 26 | `rollback_already_reversed` | Target was already rolled back. |
| 27 | `rollback_invalid_target` | Target operation is `DELETE`, `RESTORE`, or `ROLLBACK`. |

## Supplier SET arbitration

After sorting, walk events in order. The first `SET` for a given `(product_id, event_time)` that survives validation records its `supplier_id` as the timestamp owner. Later `SET` rows at that same timestamp from a different supplier fail with `supplier_conflict`. Same supplier at the same timestamp is not a supplier conflict; version and duplicate rules still apply.

## Idempotency

Canonical payload uses normalized allowed keys. Identical replays of the same `event_id` increment `skipped_idempotent_count` and do not re-apply.

## Apply semantics

`ADD`/`REMOVE`/`SET`/`DELETE`/`RESTORE`/`ROLLBACK` behave as documented in the public instruction output schema. Rollback of `SET` restores the quantity stored when that `SET` was applied. `DELETE` records which supplier deleted the product; only that supplier may `RESTORE` it. Products enter inventory state only when an event is successfully applied; rejected events do not create placeholder rows.

## Output digest

`snapshot_digest` is lowercase SHA-256 hex over the snapshot object excluding itself, with sorted keys and compact separators.
