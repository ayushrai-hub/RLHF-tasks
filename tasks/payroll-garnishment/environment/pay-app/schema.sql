-- Schema for the SQLite-backed payroll garnishment engine.
-- Monetary amounts are stored as INTEGER cents. Never use floating point.

-- employees: one row per employee. name is globally unique. gross is the
-- gross pay for the pay period in cents; mandatory is the total of the
-- legally mandated deductions (taxes, mandatory retirement) in cents that are
-- subtracted from gross to reach disposable earnings.
CREATE TABLE IF NOT EXISTS employees (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL UNIQUE,
    gross      INTEGER NOT NULL,
    mandatory  INTEGER NOT NULL
);

-- orders: one row per active garnishment order against an employee. kind names
-- the order type; priority is the integer rank used to allocate the garnishable
-- pool (lower number paid first); cap is the most that may be withheld for this
-- order in a single pay period in cents.
CREATE TABLE IF NOT EXISTS orders (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id  INTEGER NOT NULL,
    kind         TEXT NOT NULL,
    priority     INTEGER NOT NULL,
    cap          INTEGER NOT NULL
);

-- audit: the tamper-evident hash chain over a remittance run. One row per
-- remittance line in the order it was recorded. seq is 1-based and contiguous;
-- entry_hash is the lowercase-hex HMAC-SHA256 over the canonical message, and
-- prev_hash links to the prior entry (64 zeros for the genesis entry).
CREATE TABLE IF NOT EXISTS audit (
    seq          INTEGER PRIMARY KEY,
    employee_id  INTEGER NOT NULL,
    order_id     INTEGER NOT NULL,
    kind         TEXT NOT NULL,
    amount       INTEGER NOT NULL,
    prev_hash    TEXT NOT NULL,
    entry_hash   TEXT NOT NULL
);
