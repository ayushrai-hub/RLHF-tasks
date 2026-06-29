package main

// SQL table creation statements.
const (
	sqlCreateEquipment = `
CREATE TABLE IF NOT EXISTS equipment (
	equipment_id    TEXT PRIMARY KEY,
	name            TEXT NOT NULL,
	category        TEXT NOT NULL CHECK(category IN ('tool','electronics','furniture')),
	daily_rate_cents INTEGER NOT NULL,
	status          TEXT NOT NULL DEFAULT 'available'
);`

	sqlCreateBorrowers = `
CREATE TABLE IF NOT EXISTS borrowers (
	borrower_id TEXT PRIMARY KEY,
	name        TEXT NOT NULL
);`

	sqlCreateCheckouts = `
CREATE TABLE IF NOT EXISTS checkouts (
	checkout_id     INTEGER PRIMARY KEY AUTOINCREMENT,
	equipment_id    TEXT NOT NULL,
	borrower_id     TEXT NOT NULL,
	checkout_date   TEXT NOT NULL,
	checkin_date    TEXT,
	fee_cents       INTEGER,
	status          TEXT NOT NULL DEFAULT 'open',
	FOREIGN KEY(equipment_id) REFERENCES equipment(equipment_id),
	FOREIGN KEY(borrower_id) REFERENCES borrowers(borrower_id)
);`

	sqlCreateAuditChain = `
CREATE TABLE IF NOT EXISTS audit_chain (
	id              INTEGER PRIMARY KEY AUTOINCREMENT,
	chain_id        INTEGER NOT NULL,
	equipment_id    TEXT NOT NULL,
	checkout_id     INTEGER NOT NULL,
	borrower_id     TEXT NOT NULL,
	daily_rate_cents INTEGER NOT NULL,
	checkout_date   TEXT NOT NULL,
	prev_hash       TEXT NOT NULL DEFAULT '',
	hash            TEXT NOT NULL
);`
)
