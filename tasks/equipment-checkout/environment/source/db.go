package main

import (
	"database/sql"
	_ "modernc.org/sqlite"
)

// openDB opens a SQLite database at path using the modernc driver.
func openDB(path string) (*sql.DB, error) {
	return sql.Open("sqlite", path)
}
