#!/usr/bin/env bash
set -euo pipefail

# Remove stub files that will be replaced by the full implementation
rm -f /app/chain.go /app/config.go /app/db.go /app/errors.go /app/stats.go /app/version.go \
      /app/validate.go /app/logger.go /app/filters.go /app/date_utils.go /app/output.go \
      /app/migrations.go /app/queries.go /app/types.go /app/constants.go

cat > /app/cmds.go << 'GOEOF'
package main

import (
	"database/sql"
	"fmt"
	"os"
	"strconv"
	"strings"

	_ "modernc.org/sqlite"
)

func openDB(path string) (*sql.DB, error) {
	return sql.Open("sqlite", path)
}

func run(args []string) error {
	if len(args) == 0 {
		return fmt.Errorf("no command given")
	}
	switch args[0] {
	case "init":
		return cmdInit(args[1:])
	case "add-equipment":
		return cmdAddEquipment(args[1:])
	case "add-borrower":
		return cmdAddBorrower(args[1:])
	case "list-equipment":
		return cmdListEquipment(args[1:])
	default:
		return fmt.Errorf("unknown command: %s", args[0])
	}
}

func initSchema(db *sql.DB) error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS equipment (
			equipment_id     TEXT PRIMARY KEY,
			name             TEXT NOT NULL,
			category         TEXT NOT NULL CHECK(category IN ('tool','electronics','furniture')),
			daily_rate_cents INTEGER NOT NULL,
			status           TEXT NOT NULL DEFAULT 'available',
			condition        TEXT NOT NULL DEFAULT 'OK'
		)`,
		`CREATE TABLE IF NOT EXISTS borrowers (
			borrower_id TEXT PRIMARY KEY,
			name        TEXT NOT NULL
		)`,
		`CREATE TABLE IF NOT EXISTS checkouts (
			checkout_id     INTEGER PRIMARY KEY AUTOINCREMENT,
			equipment_id    TEXT NOT NULL,
			borrower_id     TEXT NOT NULL,
			checkout_date   TEXT NOT NULL,
			checkin_date    TEXT,
			fee_cents       INTEGER,
			status          TEXT NOT NULL DEFAULT 'open',
			FOREIGN KEY(equipment_id) REFERENCES equipment(equipment_id),
			FOREIGN KEY(borrower_id) REFERENCES borrowers(borrower_id)
		)`,
		`CREATE TABLE IF NOT EXISTS audit_chain (
			id               INTEGER PRIMARY KEY AUTOINCREMENT,
			chain_id         INTEGER NOT NULL,
			equipment_id     TEXT NOT NULL,
			checkout_id      INTEGER NOT NULL,
			borrower_id      TEXT NOT NULL,
			daily_rate_cents INTEGER NOT NULL,
			checkout_date    TEXT NOT NULL,
			prev_hash        TEXT NOT NULL DEFAULT '',
			hash             TEXT NOT NULL
		)`,
	}
	for _, s := range stmts {
		if _, err := db.Exec(s); err != nil {
			return err
		}
	}
	return nil
}

func cmdInit(args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("usage: init <db>")
	}
	db, err := openDB(args[0])
	if err != nil {
		return err
	}
	defer db.Close()
	if err := initSchema(db); err != nil {
		return err
	}
	fmt.Println("OK")
	return nil
}

func cmdAddEquipment(args []string) error {
	if len(args) < 5 {
		return fmt.Errorf("usage: add-equipment <db> <equipment_id> <name> <category> <daily_rate_cents> [condition]")
	}
	dbPath, equipID, name, category, rateStr := args[0], args[1], args[2], args[3], args[4]
	condition := "OK"
	if len(args) >= 6 {
		condition = args[5]
	}

	validCats := map[string]bool{"tool": true, "electronics": true, "furniture": true}
	if !validCats[category] {
		fmt.Printf("invalid category %q: must be tool|electronics|furniture\n", category)
		os.Exit(1)
	}

	validConds := map[string]bool{"OK": true, "DAMAGED": true, "MAINTENANCE": true}
	if !validConds[condition] {
		fmt.Printf("invalid condition %q: must be OK|DAMAGED|MAINTENANCE\n", condition)
		os.Exit(1)
	}

	rate, err := strconv.ParseInt(rateStr, 10, 64)
	if err != nil {
		return fmt.Errorf("daily_rate_cents must be an integer")
	}

	db, err := openDB(dbPath)
	if err != nil {
		return err
	}
	defer db.Close()

	_, err = db.Exec(
		`INSERT INTO equipment (equipment_id, name, category, daily_rate_cents, condition) VALUES (?, ?, ?, ?, ?)`,
		equipID, name, category, rate, condition)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE") {
			fmt.Printf("equipment already exists: %s\n", equipID)
			os.Exit(1)
		}
		return err
	}
	fmt.Println("OK")
	return nil
}

func cmdAddBorrower(args []string) error {
	if len(args) < 3 {
		return fmt.Errorf("usage: add-borrower <db> <borrower_id> <name>")
	}
	dbPath, borrowerID := args[0], args[1]
	name := strings.Join(args[2:], " ")

	db, err := openDB(dbPath)
	if err != nil {
		return err
	}
	defer db.Close()

	_, err = db.Exec(`INSERT INTO borrowers (borrower_id, name) VALUES (?, ?)`, borrowerID, name)
	if err != nil {
		if strings.Contains(err.Error(), "UNIQUE") {
			fmt.Printf("borrower already exists: %s\n", borrowerID)
			os.Exit(1)
		}
		return err
	}
	fmt.Println("OK")
	return nil
}

func cmdListEquipment(args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("usage: list-equipment <db>")
	}
	db, err := openDB(args[0])
	if err != nil {
		return err
	}
	defer db.Close()

	rows, err := db.Query(
		`SELECT equipment_id, name, category, daily_rate_cents, status, condition FROM equipment ORDER BY equipment_id ASC`)
	if err != nil {
		return err
	}
	defer rows.Close()

	for rows.Next() {
		var eid, name, cat, status, cond string
		var rate int64
		if err := rows.Scan(&eid, &name, &cat, &rate, &status, &cond); err != nil {
			return err
		}
		fmt.Printf("%s\t%s\t%s\t%d\t%s\t%s\n", eid, name, cat, rate, status, cond)
	}
	return rows.Err()
}
GOEOF

cat > /app/helpers.go << 'GOEOF'
package main

import (
	"math"
	"time"
)

func dateDiffDays(from, to string) int64 {
	t1, _ := time.Parse("2006-01-02", from)
	t2, _ := time.Parse("2006-01-02", to)
	return int64(t2.Sub(t1).Hours() / 24)
}

func nearestRankF(sorted []float64, q float64) float64 {
	n := len(sorted)
	if n == 0 {
		return 0
	}
	rank := int(math.Ceil(q * float64(n)))
	if rank < 1 {
		rank = 1
	}
	if rank > n {
		rank = n
	}
	return sorted[rank-1]
}

func popStddev(values []float64) float64 {
	n := float64(len(values))
	if n == 0 {
		return 0
	}
	var sum float64
	for _, v := range values {
		sum += v
	}
	mean := sum / n
	var variance float64
	for _, v := range values {
		d := v - mean
		variance += d * d
	}
	variance /= n
	return math.Sqrt(variance)
}

func bankersRound(f float64) int64 {
	floor := int64(math.Floor(f))
	frac := f - float64(floor)
	if math.Abs(frac-0.5) < 1e-9 {
		if floor%2 == 0 {
			return floor
		}
		return floor + 1
	}
	return int64(math.Round(f))
}
GOEOF

cd /app && go build -o /app/app .
