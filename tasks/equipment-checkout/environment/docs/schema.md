# Database Schema

All tables are created by the `init` command.

## equipment

| Column           | Type    | Notes                                                       |
|------------------|---------|-------------------------------------------------------------|
| equipment_id     | TEXT PK | Unique identifier                                           |
| name             | TEXT    | Human-readable name                                         |
| category         | TEXT    | One of: tool, electronics, furniture                        |
| daily_rate_cents | INTEGER | Rental cost per day in cents                                |
| status           | TEXT    | available or checked_out (default: available)               |
| condition        | TEXT    | OK, DAMAGED, or MAINTENANCE (default: OK). See `/docs/equipment-policies.md` |

## borrowers

| Column      | Type    | Notes             |
|-------------|---------|-------------------|
| borrower_id | TEXT PK | Unique identifier |
| name        | TEXT    | Full name         |

## checkouts

| Column          | Type    | Notes                             |
|-----------------|---------|-----------------------------------|
| checkout_id     | INTEGER | Auto-increment primary key        |
| equipment_id    | TEXT FK | References equipment              |
| borrower_id     | TEXT FK | References borrowers              |
| checkout_date   | TEXT    | YYYY-MM-DD                        |
| checkin_date    | TEXT    | YYYY-MM-DD, NULL if still open    |
| fee_cents       | INTEGER | Computed on checkin, NULL if open |
| status          | TEXT    | open or closed                    |

## audit_chain

| Column          | Type    | Notes                                      |
|-----------------|---------|--------------------------------------------|
| id              | INTEGER | Auto-increment primary key                 |
| chain_id        | INTEGER | Per-equipment sequence number (1, 2, 3...) |
| equipment_id    | TEXT    | References equipment                       |
| checkout_id     | INTEGER | References checkouts                       |
| borrower_id     | TEXT    | Borrower at checkout time                  |
| daily_rate_cents| INTEGER | Rate at checkout time                      |
| checkout_date   | TEXT    | YYYY-MM-DD                                 |
| prev_hash       | TEXT    | Hash of preceding chain entry ('' if first)|
| hash            | TEXT    | HMAC-SHA256 of the chain data string       |
