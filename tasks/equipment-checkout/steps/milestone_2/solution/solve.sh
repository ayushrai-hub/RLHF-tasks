#!/usr/bin/env bash
set -euo pipefail

# Remove stub files that will be replaced by the full implementation
rm -f /app/chain.go /app/config.go /app/db.go /app/errors.go /app/stats.go /app/version.go \
      /app/validate.go /app/logger.go /app/filters.go /app/date_utils.go /app/output.go \
      /app/migrations.go /app/queries.go /app/types.go /app/constants.go

cat > /app/cmds.go << 'GOEOF'
package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"fmt"
	"os"
	"strconv"
	"strings"

	_ "modernc.org/sqlite"
)

func openDB(path string) (*sql.DB, error) {
	return sql.Open("sqlite", path)
}

func computeHMACStr(key, data string) string {
	mac := hmac.New(sha256.New, []byte(key))
	mac.Write([]byte(data))
	return hex.EncodeToString(mac.Sum(nil))
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
	case "checkout":
		return cmdCheckout(args[1:])
	case "checkin":
		return cmdCheckin(args[1:])
	case "checkout-stats":
		return cmdCheckoutStats(args[1:])
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

func cmdCheckout(args []string) error {
	if len(args) < 4 {
		return fmt.Errorf("usage: checkout <db> <equipment_id> <borrower_id> <checkout_date>")
	}
	dbPath, equipID, borrowerID, checkoutDate := args[0], args[1], args[2], args[3]

	db, err := openDB(dbPath)
	if err != nil {
		return err
	}
	defer db.Close()

	var status, condition string
	var dailyRate int64
	err = db.QueryRow(
		`SELECT status, daily_rate_cents, condition FROM equipment WHERE equipment_id=?`, equipID).
		Scan(&status, &dailyRate, &condition)
	if err == sql.ErrNoRows {
		fmt.Printf("equipment not found: %s\n", equipID)
		os.Exit(1)
	} else if err != nil {
		return err
	}
	// DAMAGED equipment is treated as permanently unavailable (see /docs/equipment-policies.md)
	if status != "available" || condition == "DAMAGED" {
		fmt.Printf("equipment not available: %s\n", equipID)
		os.Exit(1)
	}

	var borrowerName string
	err = db.QueryRow(`SELECT name FROM borrowers WHERE borrower_id=?`, borrowerID).Scan(&borrowerName)
	if err == sql.ErrNoRows {
		fmt.Printf("borrower not found: %s\n", borrowerID)
		os.Exit(1)
	} else if err != nil {
		return err
	}

	tx, err := db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	res, err := tx.Exec(
		`INSERT INTO checkouts (equipment_id, borrower_id, checkout_date) VALUES (?, ?, ?)`,
		equipID, borrowerID, checkoutDate)
	if err != nil {
		return err
	}
	checkoutID, _ := res.LastInsertId()

	if _, err := tx.Exec(`UPDATE equipment SET status='checked_out' WHERE equipment_id=?`, equipID); err != nil {
		return err
	}

	// Build HMAC chain entry
	var chainCount int64
	tx.QueryRow(`SELECT COUNT(*) FROM audit_chain WHERE equipment_id=?`, equipID).Scan(&chainCount)
	chainID := chainCount + 1

	var prevHash string
	if chainCount > 0 {
		tx.QueryRow(
			`SELECT hash FROM audit_chain WHERE equipment_id=? ORDER BY chain_id DESC LIMIT 1`, equipID).
			Scan(&prevHash)
	}

	data := fmt.Sprintf("%d|CHECKOUT|%d|%s|%s|%d|%s|%s",
		chainID, checkoutID, equipID, borrowerID, dailyRate, checkoutDate, prevHash)
	hash := computeHMACStr("equipment-checkout-secret-2026", data)

	if _, err := tx.Exec(
		`INSERT INTO audit_chain (chain_id, equipment_id, checkout_id, borrower_id, daily_rate_cents, checkout_date, prev_hash, hash) VALUES (?,?,?,?,?,?,?,?)`,
		chainID, equipID, checkoutID, borrowerID, dailyRate, checkoutDate, prevHash, hash,
	); err != nil {
		return err
	}

	if err := tx.Commit(); err != nil {
		return err
	}

	fmt.Printf("OK checkout_id=%d\n", checkoutID)
	return nil
}

func cmdCheckin(args []string) error {
	if len(args) < 3 {
		return fmt.Errorf("usage: checkin <db> <checkout_id> <checkin_date>")
	}
	dbPath, cidStr, checkinDate := args[0], args[1], args[2]

	checkoutID, err := strconv.ParseInt(cidStr, 10, 64)
	if err != nil {
		return fmt.Errorf("checkout_id must be an integer")
	}

	db, err := openDB(dbPath)
	if err != nil {
		return err
	}
	defer db.Close()

	var equipID, checkoutDate, coStatus string
	err = db.QueryRow(
		`SELECT equipment_id, checkout_date, status FROM checkouts WHERE checkout_id=?`, checkoutID).
		Scan(&equipID, &checkoutDate, &coStatus)
	if err == sql.ErrNoRows {
		fmt.Printf("checkout not found: %d\n", checkoutID)
		os.Exit(1)
	} else if err != nil {
		return err
	}
	if coStatus != "open" {
		fmt.Printf("checkout already closed: %d\n", checkoutID)
		os.Exit(1)
	}

	var dailyRate int64
	var condition string
	db.QueryRow(
		`SELECT daily_rate_cents, condition FROM equipment WHERE equipment_id=?`, equipID).
		Scan(&dailyRate, &condition)

	days := dateDiffDays(checkoutDate, checkinDate)
	feeCents := days * dailyRate
	// MAINTENANCE surcharge: multiply by 1.5 with banker's rounding (see /docs/equipment-policies.md)
	if condition == "MAINTENANCE" {
		feeCents = bankersRound(float64(feeCents) * 1.5)
	}

	if _, err := db.Exec(
		`UPDATE checkouts SET checkin_date=?, fee_cents=?, status='closed' WHERE checkout_id=?`,
		checkinDate, feeCents, checkoutID); err != nil {
		return err
	}
	if _, err := db.Exec(`UPDATE equipment SET status='available' WHERE equipment_id=?`, equipID); err != nil {
		return err
	}

	fmt.Printf("OK fee_cents=%d\n", feeCents)
	return nil
}

func cmdCheckoutStats(args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("usage: checkout-stats <db>")
	}
	db, err := openDB(args[0])
	if err != nil {
		return err
	}
	defer db.Close()

	var total, returned int64
	db.QueryRow(`SELECT COUNT(*) FROM checkouts`).Scan(&total)
	db.QueryRow(`SELECT COUNT(*) FROM checkouts WHERE status='closed'`).Scan(&returned)

	var avg float64
	var totalFee int64
	if returned > 0 {
		db.QueryRow(
			`SELECT AVG(fee_cents), COALESCE(SUM(fee_cents), 0) FROM checkouts WHERE status='closed'`).
			Scan(&avg, &totalFee)
	}

	fmt.Printf("total_checkouts=%d\n", total)
	fmt.Printf("total_returned=%d\n", returned)
	fmt.Printf("total_fee_cents=%d\n", totalFee)
	fmt.Printf("avg_fee_cents=%.2f\n", avg)
	return nil
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

// bankersRound applies HALF_EVEN (banker's) rounding: .5 rounds to nearest even integer.
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
