package main

import "database/sql"

// runMigrations creates all required tables if they do not exist.
func runMigrations(db *sql.DB) error {
	for _, stmt := range []string{
		sqlCreateEquipment,
		sqlCreateBorrowers,
		sqlCreateCheckouts,
		sqlCreateAuditChain,
	} {
		if _, err := db.Exec(stmt); err != nil {
			return err
		}
	}
	return nil
}
