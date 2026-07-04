#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/app"

# ── employees.go ─────────────────────────────────────────────────────────────
cat > "$APP_DIR/employees.go" << 'GOEOF'
package main

import (
	"fmt"
	"strconv"
	"strings"
)

// LookupEmployee returns the employee with the given name, or nil when unknown.
func LookupEmployee(name string) (*Employee, error) {
	rows, err := sqliteQuery(fmt.Sprintf(
		"SELECT id, gross, mandatory FROM employees WHERE name = %s LIMIT 1;",
		sqlQuote(name),
	))
	if err != nil {
		return nil, err
	}
	if len(rows) == 0 || strings.TrimSpace(rows[0]) == "" {
		return nil, nil
	}
	parts := strings.SplitN(rows[0], "|", 3)
	if len(parts) < 3 {
		return nil, nil
	}
	var e Employee
	e.Name = name
	e.ID, _ = strconv.ParseInt(strings.TrimSpace(parts[0]), 10, 64)
	e.Gross, _ = strconv.ParseInt(strings.TrimSpace(parts[1]), 10, 64)
	e.Mandatory, _ = strconv.ParseInt(strings.TrimSpace(parts[2]), 10, 64)
	return &e, nil
}

// AddEmployee creates a new employee and returns the new id, or "exists".
func AddEmployee(name string, gross, mandatory int64) (int64, error) {
	existing, err := LookupEmployee(name)
	if err != nil {
		return 0, err
	}
	if existing != nil {
		return 0, fmt.Errorf("exists")
	}
	if _, err := sqliteExec(fmt.Sprintf(
		"INSERT INTO employees (name, gross, mandatory) VALUES (%s, %d, %d);",
		sqlQuote(name), gross, mandatory,
	)); err != nil {
		return 0, err
	}
	e, err := LookupEmployee(name)
	if err != nil {
		return 0, err
	}
	if e == nil {
		return 0, fmt.Errorf("insert failed")
	}
	return e.ID, nil
}

// ListEmployees returns every employee sorted by name.
func ListEmployees() ([]Employee, error) {
	rows, err := sqliteQuery(
		"SELECT id, name, gross, mandatory FROM employees ORDER BY name;",
	)
	if err != nil {
		return nil, err
	}
	out := []Employee{}
	for _, r := range rows {
		if strings.TrimSpace(r) == "" {
			continue
		}
		parts := strings.SplitN(r, "|", 4)
		if len(parts) < 4 {
			continue
		}
		var e Employee
		e.ID, _ = strconv.ParseInt(strings.TrimSpace(parts[0]), 10, 64)
		e.Name = parts[1]
		e.Gross, _ = strconv.ParseInt(strings.TrimSpace(parts[2]), 10, 64)
		e.Mandatory, _ = strconv.ParseInt(strings.TrimSpace(parts[3]), 10, 64)
		out = append(out, e)
	}
	return out, nil
}

// AddOrder records a garnishment order and returns the new id. The INSERT and
// the last_insert_rowid() lookup run in a single sqlite3 invocation so the
// rowid survives.
func AddOrder(employeeID int64, kind string, priority, cap int64) (int64, error) {
	out, err := sqliteExec(fmt.Sprintf(
		"INSERT INTO orders (employee_id, kind, priority, cap) VALUES (%d, %s, %d, %d);"+
			"SELECT last_insert_rowid();",
		employeeID, sqlQuote(kind), priority, cap,
	))
	if err != nil {
		return 0, err
	}
	id, _ := strconv.ParseInt(strings.TrimSpace(out), 10, 64)
	return id, nil
}

// ListOrders returns an employee's orders ordered by priority then id.
func ListOrders(employeeID int64) ([]Order, error) {
	rows, err := sqliteQuery(fmt.Sprintf(
		"SELECT id, employee_id, kind, priority, cap FROM orders "+
			"WHERE employee_id = %d ORDER BY priority, id;", employeeID,
	))
	if err != nil {
		return nil, err
	}
	out := []Order{}
	for _, r := range rows {
		if strings.TrimSpace(r) == "" {
			continue
		}
		parts := strings.SplitN(r, "|", 5)
		if len(parts) < 5 {
			continue
		}
		var o Order
		o.ID, _ = strconv.ParseInt(strings.TrimSpace(parts[0]), 10, 64)
		o.EmployeeID, _ = strconv.ParseInt(strings.TrimSpace(parts[1]), 10, 64)
		o.Kind = parts[2]
		o.Priority, _ = strconv.ParseInt(strings.TrimSpace(parts[3]), 10, 64)
		o.Cap, _ = strconv.ParseInt(strings.TrimSpace(parts[4]), 10, 64)
		out = append(out, o)
	}
	return out, nil
}
GOEOF

# ── parse.go ─────────────────────────────────────────────────────────────────
cat > "$APP_DIR/parse.go" << 'GOEOF'
package main

import (
	"fmt"
	"strconv"
)

// splitFlags parses "--name value" pairs out of args, returning the flag map and
// the remaining positionals.
func splitFlags(args []string, valueFlags map[string]bool) (map[string]string, []string, error) {
	flags := map[string]string{}
	pos := []string{}
	i := 0
	for i < len(args) {
		a := args[i]
		if len(a) > 2 && a[:2] == "--" {
			if !valueFlags[a] {
				return nil, nil, fmt.Errorf("unknown flag: %s", a)
			}
			if i+1 >= len(args) {
				return nil, nil, fmt.Errorf("%s requires a value", a)
			}
			flags[a] = args[i+1]
			i += 2
			continue
		}
		pos = append(pos, a)
		i++
	}
	return flags, pos, nil
}

// parseIntFlag parses a flag's value as a base-10 integer, rejecting fractional
// or non-numeric values.
func parseIntFlag(flags map[string]string, name string) (int64, bool) {
	s, ok := flags[name]
	if !ok {
		return 0, false
	}
	n, err := strconv.ParseInt(s, 10, 64)
	if err != nil {
		return 0, false
	}
	return n, true
}
GOEOF

# ── cli.go ───────────────────────────────────────────────────────────────────
cat > "$APP_DIR/cli.go" << 'GOEOF'
package main

import (
	"fmt"
	"os"
)

// requireEmployee looks up the employee, printing not_found and exiting when
// absent.
func requireEmployee(name string) *Employee {
	e, err := LookupEmployee(name)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if e == nil {
		fmt.Println("not_found")
		os.Exit(1)
	}
	return e
}

// badInput prints bad_input and exits non-zero.
func badInput() {
	fmt.Println("bad_input")
	os.Exit(1)
}

// CmdInit handles `pay init`.
func CmdInit() {
	if err := InitDB(); err != nil {
		fmt.Fprintf(os.Stderr, "init error: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("ok")
}

// CmdAddEmployee handles `pay add-employee <name> --gross <c> --mandatory <c>`.
func CmdAddEmployee(args []string) {
	flags, pos, err := splitFlags(args, map[string]bool{
		"--gross": true, "--mandatory": true,
	})
	if err != nil || len(pos) < 1 {
		fmt.Fprintln(os.Stderr, "usage: pay add-employee <name> --gross <c> --mandatory <c>")
		os.Exit(1)
	}
	gross, okG := parseIntFlag(flags, "--gross")
	mandatory, okM := parseIntFlag(flags, "--mandatory")
	if !okG || !okM || gross <= 0 || mandatory < 0 || mandatory > gross {
		badInput()
	}
	id, err := AddEmployee(pos[0], gross, mandatory)
	if err != nil {
		if err.Error() == "exists" {
			fmt.Println("exists")
			os.Exit(1)
		}
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(id)
}

// CmdAddOrder handles `pay add-order <employee> --kind --priority --cap`.
func CmdAddOrder(args []string) {
	flags, pos, err := splitFlags(args, map[string]bool{
		"--kind": true, "--priority": true, "--cap": true,
	})
	if err != nil || len(pos) < 1 {
		fmt.Fprintln(os.Stderr, "usage: pay add-order <employee> --kind <k> --priority <n> --cap <c>")
		os.Exit(1)
	}
	kind, okK := flags["--kind"]
	priority, okP := parseIntFlag(flags, "--priority")
	cap, okC := parseIntFlag(flags, "--cap")
	if !okK || kind == "" || !okP || priority <= 0 || !okC || cap <= 0 {
		badInput()
	}
	e := requireEmployee(pos[0])
	id, err := AddOrder(e.ID, kind, priority, cap)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(id)
}

// CmdEmployees handles `pay employees`.
func CmdEmployees(args []string) {
	_ = args
	es, err := ListEmployees()
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	for _, e := range es {
		fmt.Printf("%d %s %d %d\n", e.ID, e.Name, e.Gross, e.Mandatory)
	}
}

// CmdOrders handles `pay orders <employee>`.
func CmdOrders(args []string) {
	flags, pos, err := splitFlags(args, map[string]bool{})
	_ = flags
	if err != nil || len(pos) < 1 {
		fmt.Fprintln(os.Stderr, "usage: pay orders <employee>")
		os.Exit(1)
	}
	e := requireEmployee(pos[0])
	os_, err := ListOrders(e.ID)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	for _, o := range os_ {
		fmt.Printf("%d %s %d %d\n", o.ID, o.Kind, o.Priority, o.Cap)
	}
}

// CmdNet handles `pay net <gross>`.
func CmdNet(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
}

// CmdGrossup handles `pay grossup <target>`.
func CmdGrossup(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
}

// CmdTargetGross handles `pay target-gross <employee> <target-net>`.
func CmdTargetGross(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
}

// CmdAllocate handles `pay allocate <employee> <gross>`.
func CmdAllocate(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
}

// CmdProject handles `pay project <employee> --gross <c> --periods <n> [--exempt <k>]`.
func CmdProject(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
}

// CmdStats handles `pay stats <employee>`.
func CmdStats(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
}

// CmdRemit handles `pay remit <employee>`.
func CmdRemit(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
}

// CmdAudit handles `pay audit`.
func CmdAudit(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
}

// CmdAuditVerify handles `pay audit-verify [--chain <base64-json>]`.
func CmdAuditVerify(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
}
GOEOF

cd "$APP_DIR"
gofmt -w employees.go parse.go cli.go
go build -o /app/pay .
echo "Build successful: /app/pay"
