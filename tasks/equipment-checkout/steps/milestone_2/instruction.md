# Milestone 2 — Checkout, Checkin and Stats

Implement three additional commands. All prior commands must still work.

## Commands

### `checkout <db> <equipment_id> <borrower_id> <checkout_date>`
Check out equipment to a borrower. Validation order (print to stdout, exit 1):
1. `equipment not found: <equipment_id>` — if equipment does not exist
2. `equipment not available: <equipment_id>` — if status is not `available` **or** condition is `DAMAGED`
3. `borrower not found: <borrower_id>` — if borrower does not exist

See `/docs/equipment-policies.md` for full DAMAGED equipment rules.

On success:
- Insert a row into `checkouts` with status `open`.
- Update `equipment.status` to `checked_out`.
- Append one HMAC chain entry to `audit_chain` (see `/docs/chain-spec.md`).
- Print: `OK checkout_id=<N>`

### `checkin <db> <checkout_id> <checkin_date>`
Return equipment. Validation (print to stdout, exit 1):
1. `checkout not found: <checkout_id>` — if the checkout does not exist
2. `checkout already closed: <checkout_id>` — if status is not `open`

On success:
- Compute `days_elapsed = (checkin_date - checkout_date)` in whole days.
- Compute base `fee_cents = days_elapsed × daily_rate_cents`.
- If the equipment's `condition` is `MAINTENANCE`, apply the 1.5× surcharge with banker's rounding. See `/docs/equipment-policies.md` for the exact formula and rounding rules.
- Update checkout with `checkin_date`, `fee_cents` (surcharge-adjusted if applicable), status `closed`.
- Update `equipment.status` to `available`.
- Print: `OK fee_cents=<N>`

### `checkout-stats <db>`
Print aggregate statistics:

    total_checkouts=<N>
    total_returned=<N>
    total_fee_cents=<N>
    avg_fee_cents=<value to 2 decimal places>

`total_checkouts` counts all rows in checkouts. `total_returned` counts closed checkouts. `total_fee_cents` is the sum of fee_cents of all closed checkouts (0 if none). `avg_fee_cents` is the average fee of closed checkouts (0.00 if none).

## References
Chain spec: `/docs/chain-spec.md` — Schema: `/docs/schema.md` — Equipment policies: `/docs/equipment-policies.md`
