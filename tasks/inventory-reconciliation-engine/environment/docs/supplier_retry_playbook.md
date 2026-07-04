# Supplier retry playbook (draft)

When suppliers retry failed uploads, downstream systems should treat identical
`event_id` values as safe no-ops.

## SET timestamp collisions (draft policy — superseded)

When two suppliers `SET` the same SKU at the same second, legacy reconcilers kept
the row with the lexicographically **highest** `supplier_id`. Do **not** implement
that rule for current production — the live contract uses first-writer-wins in
sorted replay order. See `/app/docs/reconciliation_rules.md`.

## Open questions

- Whether version numbers monotonically increase per supplier SKU stream
- Whether rollbacks can target DELETE events

Consult the current reconciler contract before changing production behavior.
