# Audit Chain Specification

Each equipment item has its own independent HMAC-SHA256 chain stored in the `audit_chain` table.

## Insertion Procedure (on checkout)

1. Count existing rows for `equipment_id` → `chain_id = count + 1`
2. If `chain_id == 1`, `prev_hash = ""`; otherwise fetch `hash` of the row with the highest `chain_id` for this equipment.
3. Build the data string:

       <chain_id>|CHECKOUT|<checkout_id>|<equipment_id>|<borrower_id>|<daily_rate_cents>|<checkout_date>|<prev_hash>

4. Compute `hash = HMAC-SHA256("equipment-checkout-secret-2026", data_string)` encoded as lowercase hex.
5. Insert the row into `audit_chain`.

## Verification (chain-verify)

For each equipment, fetch its chain rows ordered by `chain_id ASC`. For each row:

1. Recompute `prev_hash`: `""` for the first entry, else the `hash` of the preceding row.
2. Recompute `hash` using the same data string formula.
3. If either value differs from stored, report: `TAMPERED <equipment_id> <chain_id>`

Scan every row before deciding exit code. Exit 1 if any tampering found, exit 0 otherwise.
