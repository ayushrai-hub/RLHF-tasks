# CLI API Specification

Binary: `/app/app`  
Database path is always the first positional argument after the command name.

## Milestone 1

- `init <db>` — Create tables. Idempotent. Prints `OK`.
- `add-equipment <db> <equipment_id> <name> <category> <daily_rate_cents> [condition]` — Add equipment. Category must be tool|electronics|furniture. Optional `condition` must be OK|DAMAGED|MAINTENANCE (default: OK). Prints `OK`. Duplicate equipment_id → print error to stdout, exit 1. Invalid category or condition → print error, exit 1.
- `add-borrower <db> <borrower_id> <name>` — Add borrower. Prints `OK`. Duplicate borrower_id → print error to stdout, exit 1.
- `list-equipment <db>` — Tab-separated: equipment_id, name, category, daily_rate_cents, status, condition. Sorted by equipment_id ASC.

## Milestone 2

- `checkout <db> <equipment_id> <borrower_id> <checkout_date>` — Checkout equipment. Prints `OK checkout_id=<N>`. Errors to stdout, exit 1. See `/docs/equipment-policies.md` for DAMAGED handling.
- `checkin <db> <checkout_id> <checkin_date>` — Return equipment. Prints `OK fee_cents=<N>`. Errors to stdout, exit 1. See `/docs/equipment-policies.md` for MAINTENANCE fee surcharge.
- `checkout-stats <db>` — Prints total_checkouts, total_returned, total_fee_cents (integer sum), avg_fee_cents to 2dp.

## Milestone 3

- `chain-verify <db>` — Verifies per-equipment HMAC chains using the rate stored in `audit_chain` (not the current equipment rate). Prints `TAMPERED <equipment_id> <chain_id>` for bad entries. Exit 1 if any tampering.
- `rental-report <db>` — Prints total_rentals, p50_fee_cents, p90_fee_cents, p95_fee_cents, std_fee_cents (population stddev) to 2dp. See `/docs/statistics-spec.md`.
