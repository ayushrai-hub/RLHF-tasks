# Equipment Condition Policies

Each equipment item carries a `condition` field that governs checkout eligibility and fee
computation. Agents **must** implement these rules; they are not optional.

## Condition Values

| Value         | Meaning                                                   |
|---------------|-----------------------------------------------------------|
| `OK`          | Normal operating condition. No special handling required. |
| `DAMAGED`     | Non-functional. Cannot be checked out under any circumstances. |
| `MAINTENANCE` | Scheduled maintenance. Checkout allowed, but rental fees carry a 1.5× surcharge. |

## Rule 1 — DAMAGED Equipment is Permanently Unavailable

When `checkout` is called for equipment whose `condition = DAMAGED`, treat it as unavailable
**regardless** of the `status` field. Print to stdout and exit 1:

    equipment not available: <equipment_id>

This check is part of the availability gate (step 2 in the validation order), alongside the
`status = checked_out` check.

## Rule 2 — MAINTENANCE Fee Surcharge (Banker's Rounding)

When `checkin` is called for equipment whose `condition = MAINTENANCE`, apply a 1.5×
surcharge to the computed fee:

    fee_cents = banker_round(days_elapsed × daily_rate_cents × 1.5)

Use **banker's rounding** (HALF_EVEN): when the product ends in exactly .5, round to the
nearest **even** integer. In all other cases use standard rounding.

Examples:

| days | daily_rate_cents | raw product | rounded fee_cents |
|------|-----------------|-------------|-------------------|
| 3    | 101             | 454.5       | 454  (454 is even) |
| 3    | 103             | 463.5       | 464  (463 is odd → round up) |
| 3    | 200             | 900.0       | 900  (exact, no rounding) |
| 1    | 103             | 154.5       | 154  (154 is even → round down) |

The `fee_cents` stored in `checkouts` must reflect the surcharge-adjusted amount.
