#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/app"

# ── audit.go ─────────────────────────────────────────────────────────────────
cat > "$APP_DIR/audit.go" << 'GOEOF'
package main

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"strconv"
	"strings"
)

const genesisHash = "0000000000000000000000000000000000000000000000000000000000000000"

// AuditSecret returns the HMAC key from PAY_AUDIT_SECRET, or the default.
func AuditSecret() string {
	if s := os.Getenv("PAY_AUDIT_SECRET"); s != "" {
		return s
	}
	return "pay-audit-key"
}

// canonicalMessage builds the exact ASCII message hashed for an audit entry.
func canonicalMessage(seq, employeeID, orderID int64, kind string, amount int64, prevHash string) string {
	return fmt.Sprintf("%d|%d|%d|%s|%d|%s", seq, employeeID, orderID, kind, amount, prevHash)
}

// computeEntryHash returns the lowercase-hex HMAC-SHA256 of an entry's message.
func computeEntryHash(seq, employeeID, orderID int64, kind string, amount int64, prevHash string) string {
	msg := canonicalMessage(seq, employeeID, orderID, kind, amount, prevHash)
	mac := hmac.New(sha256.New, []byte(AuditSecret()))
	mac.Write([]byte(msg))
	return hex.EncodeToString(mac.Sum(nil))
}

// AuditChain returns the stored audit chain ordered by seq.
func AuditChain() ([]AuditEntry, error) {
	rows, err := sqliteQuery(
		"SELECT seq, employee_id, order_id, kind, amount, prev_hash, entry_hash " +
			"FROM audit ORDER BY seq;",
	)
	if err != nil {
		return nil, err
	}
	out := []AuditEntry{}
	for _, r := range rows {
		if strings.TrimSpace(r) == "" {
			continue
		}
		parts := strings.SplitN(r, "|", 7)
		if len(parts) < 7 {
			continue
		}
		var e AuditEntry
		e.Seq, _ = strconv.ParseInt(strings.TrimSpace(parts[0]), 10, 64)
		e.EmployeeID, _ = strconv.ParseInt(strings.TrimSpace(parts[1]), 10, 64)
		e.OrderID, _ = strconv.ParseInt(strings.TrimSpace(parts[2]), 10, 64)
		e.Kind = parts[3]
		e.Amount, _ = strconv.ParseInt(strings.TrimSpace(parts[4]), 10, 64)
		e.PrevHash = strings.TrimSpace(parts[5])
		e.EntryHash = strings.TrimSpace(parts[6])
		out = append(out, e)
	}
	return out, nil
}

// AppendAudit appends one audit entry for a remittance line.
func AppendAudit(employeeID int64, r Remit) error {
	rows, err := sqliteQuery("SELECT COALESCE(MAX(seq), 0) FROM audit;")
	if err != nil {
		return err
	}
	var maxSeq int64
	if len(rows) > 0 {
		maxSeq, _ = strconv.ParseInt(strings.TrimSpace(rows[0]), 10, 64)
	}
	seq := maxSeq + 1
	prevHash := genesisHash
	if seq > 1 {
		hrows, err := sqliteQuery(fmt.Sprintf(
			"SELECT entry_hash FROM audit WHERE seq = %d LIMIT 1;", seq-1,
		))
		if err != nil {
			return err
		}
		if len(hrows) > 0 {
			prevHash = strings.TrimSpace(hrows[0])
		}
	}
	entryHash := computeEntryHash(seq, employeeID, r.Order.ID, r.Order.Kind, r.Amount, prevHash)
	_, err = sqliteExec(fmt.Sprintf(
		"INSERT INTO audit (seq, employee_id, order_id, kind, amount, prev_hash, entry_hash) "+
			"VALUES (%d, %d, %d, %s, %d, %s, %s);",
		seq, employeeID, r.Order.ID, sqlQuote(r.Order.Kind), r.Amount,
		sqlQuote(prevHash), sqlQuote(entryHash),
	))
	return err
}

// VerifyChain recomputes the chain and reports the first break, following the
// precedence seq_gap, prev_hash_mismatch, entry_hash_mismatch.
func VerifyChain(entries []AuditEntry) (bool, int64, string) {
	prevHash := genesisHash
	for i, e := range entries {
		expectSeq := int64(i + 1)
		if e.Seq != expectSeq {
			return false, expectSeq, "seq_gap"
		}
		if e.PrevHash != prevHash {
			return false, e.Seq, "prev_hash_mismatch"
		}
		want := computeEntryHash(e.Seq, e.EmployeeID, e.OrderID, e.Kind, e.Amount, e.PrevHash)
		if e.EntryHash != want {
			return false, e.Seq, "entry_hash_mismatch"
		}
		prevHash = e.EntryHash
	}
	return true, 0, ""
}
GOEOF

# ── chain.go ─────────────────────────────────────────────────────────────────
cat > "$APP_DIR/chain.go" << 'GOEOF'
package main

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
)

type chainEntryJSON struct {
	Seq        int64  `json:"seq"`
	EmployeeID int64  `json:"employee_id"`
	OrderID    int64  `json:"order_id"`
	Kind       string `json:"kind"`
	Amount     int64  `json:"amount"`
	PrevHash   string `json:"prev_hash"`
	EntryHash  string `json:"entry_hash"`
}

// ParseChain decodes a base64 JSON array of audit entries for external
// verification.
func ParseChain(b64 string) ([]AuditEntry, error) {
	raw, err := base64.StdEncoding.DecodeString(b64)
	if err != nil {
		return nil, fmt.Errorf("invalid base64: %w", err)
	}
	var items []chainEntryJSON
	if err := json.Unmarshal(raw, &items); err != nil {
		return nil, fmt.Errorf("invalid json: %w", err)
	}
	out := make([]AuditEntry, 0, len(items))
	for _, it := range items {
		out = append(out, AuditEntry{
			Seq:        it.Seq,
			EmployeeID: it.EmployeeID,
			OrderID:    it.OrderID,
			Kind:       it.Kind,
			Amount:     it.Amount,
			PrevHash:   it.PrevHash,
			EntryHash:  it.EntryHash,
		})
	}
	return out, nil
}
GOEOF

# ── patch cli.go: CmdRemit, CmdAudit, CmdAuditVerify ─────────────────────────
python3 - "$APP_DIR/cli.go" << 'PYEOF'
import sys
path = sys.argv[1]
src = open(path).read()

def replace_func(src, name, new_func):
    start = src.index(f"func {name}(")
    i = src.index("{", start)
    depth = 0
    j = i
    while j < len(src):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return src[:start] + new_func.strip() + src[j + 1:]

cmd_remit = '''
func CmdRemit(args []string) {
	flags, pos, err := splitFlags(args, map[string]bool{})
	_ = flags
	if err != nil || len(pos) < 1 {
		fmt.Fprintln(os.Stderr, "usage: pay remit <employee>")
		os.Exit(1)
	}
	e := requireEmployee(pos[0])
	orders, err := ListOrders(e.ID)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	remits := make([]Remit, 0, len(orders))
	for _, o := range orders {
		remits = append(remits, Remit{Order: o, Amount: Grossup(o.Cap)})
	}
	for _, r := range remits {
		if err := AppendAudit(e.ID, r); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	}
	for _, r := range remits {
		fmt.Printf("%d %s %d\\n", r.Order.ID, r.Order.Kind, r.Amount)
	}
}
'''

cmd_audit = '''
func CmdAudit(args []string) {
	_ = args
	chain, err := AuditChain()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	for _, e := range chain {
		fmt.Printf("%d %d %d %s %d %s\\n", e.Seq, e.EmployeeID, e.OrderID, e.Kind, e.Amount, e.EntryHash)
	}
}
'''

cmd_verify = '''
func CmdAuditVerify(args []string) {
	flags, _, err := splitFlags(args, map[string]bool{"--chain": true})
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	var entries []AuditEntry
	if b64, ok := flags["--chain"]; ok {
		entries, err = ParseChain(b64)
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	} else {
		entries, err = AuditChain()
		if err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	}
	ok, seq, reason := VerifyChain(entries)
	if ok {
		fmt.Println("valid")
		return
	}
	fmt.Printf("broken_at %d %s\\n", seq, reason)
}
'''

src = replace_func(src, "CmdRemit", cmd_remit)
src = replace_func(src, "CmdAudit", cmd_audit)
src = replace_func(src, "CmdAuditVerify", cmd_verify)
open(path, "w").write(src)
PYEOF

cd "$APP_DIR"
gofmt -w audit.go chain.go cli.go
go build -o /app/pay .
echo "Build successful: /app/pay"
