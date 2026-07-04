package main

import (
	"fmt"
	"os"
)

func usage() {
	fmt.Fprintf(os.Stderr, `pay - a payroll net-to-gross CLI backed by SQLite

Usage:
  pay init
  pay add-employee <name> --gross <cents> --mandatory <cents>
  pay add-order <employee> --kind <kind> --priority <n> --cap <cents>
  pay employees
  pay orders <employee>
  pay net <gross>
  pay grossup <target>
  pay target-gross <employee> <target-net>
  pay allocate <employee> <gross>
  pay project <employee> --gross <cents> --periods <n> [--exempt <k>]
  pay stats <employee>
  pay remit <employee>
  pay audit
  pay audit-verify [--chain <base64-json>]

Options:
  --gross <cents>        gross pay for the period (add-employee)
  --mandatory <cents>    mandated deductions in cents (add-employee)
  --kind <kind>          garnishment order kind (add-order)
  --priority <n>         allocation rank, lower paid first (add-order)
  --cap <cents>          per-order absolute cap in cents (add-order)
  --periods <n>          number of pay periods to simulate (project)
  --exempt <k>           claimed exemptions raising the protected floor (project)
  --chain <b64>          base64-encoded JSON audit chain (audit-verify)

Environment:
  PAY_AUDIT_SECRET   HMAC key for the audit chain
`)
}

func main() {
	if len(os.Args) < 2 {
		usage()
		os.Exit(1)
	}

	cmd := os.Args[1]
	rest := os.Args[2:]

	switch cmd {
	case "init":
		CmdInit()
	case "add-employee":
		CmdAddEmployee(rest)
	case "add-order":
		CmdAddOrder(rest)
	case "employees":
		CmdEmployees(rest)
	case "orders":
		CmdOrders(rest)
	case "net":
		CmdNet(rest)
	case "grossup":
		CmdGrossup(rest)
	case "target-gross":
		CmdTargetGross(rest)
	case "allocate":
		CmdAllocate(rest)
	case "project":
		CmdProject(rest)
	case "stats":
		CmdStats(rest)
	case "remit":
		CmdRemit(rest)
	case "audit":
		CmdAudit(rest)
	case "audit-verify":
		CmdAuditVerify(rest)
	default:
		fmt.Fprintf(os.Stderr, "unknown command: %s\n", cmd)
		usage()
		os.Exit(1)
	}
}
