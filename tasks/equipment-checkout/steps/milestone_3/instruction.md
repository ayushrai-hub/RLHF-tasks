# Milestone 3 — Chain Verification and Rental Report

Implement two commands that complete the equipment analytics system.

## Commands

### `chain-verify <db>`
Verifies the HMAC integrity of every per-equipment audit chain. Each equipment's entries are checked independently in `chain_id` ASC order.

For each entry, recompute:

    HMAC-SHA256("equipment-checkout-secret-2026", "<chain_id>|CHECKOUT|<checkout_id>|<equipment_id>|<borrower_id>|<daily_rate_cents>|<checkout_date>|<prev_hash>")

The `daily_rate_cents` used for recomputation **must be read from the `audit_chain` table** (the rate stored at checkout time), not from the current `equipment` table. Equipment rates may change after checkout; the chain records the historical rate.

Report any row where the recomputed hash differs from `hash`, or where `prev_hash` does not match the preceding entry's `hash` (or `""` for the first entry per equipment):

    TAMPERED <equipment_id> <chain_id>

Check every row across all equipment chains before deciding exit code. Exit 1 if any tampering found, exit 0 otherwise (no output on success).

### `rental-report <db>`
Print statistics over all completed (closed) checkout fees using population standard deviation and nearest-rank percentiles:

    total_rentals=<N>
    p50_fee_cents=<value 2dp>
    p90_fee_cents=<value 2dp>
    p95_fee_cents=<value 2dp>
    std_fee_cents=<value 2dp>
    p90_duration_minutes=<value 2dp>

**Nearest-rank (fees):** `rank = ceil(q × n)`, clamp to [1, n], return `sorted[rank-1]`.
**Population stddev:** divide variance by N (not N-1). Do NOT divide by N-1 (sample stddev).
**p90_duration_minutes:** For each closed checkout compute `days_elapsed × 1440` (minutes). Sort all durations ascending, apply nearest-rank at q=0.90: `rank = ceil(0.9 × n)`, return `sorted_durations[rank-1]`.

Fee boundary example: for n=7 fees, p90 → ceil(0.9×7) = ceil(6.3) = 7 → sorted[6]. Using floor gives the wrong element.

Duration boundary example: for n=11 rentals, p90_duration → ceil(0.9×11) = ceil(9.9) = 10 → sorted_durations[9]. Using floor(9.9)=9 → sorted_durations[8] is WRONG.

All values formatted to 2 decimal places. If no completed rentals exist, all numeric fields are `0.00` and `total_rentals=0`.

## References
Chain spec: `/docs/chain-spec.md` — Statistics spec: `/docs/statistics-spec.md` — Equipment policies: `/docs/equipment-policies.md`
