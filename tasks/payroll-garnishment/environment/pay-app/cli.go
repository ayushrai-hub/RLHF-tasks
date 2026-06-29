package main

import (
	"fmt"
	"os"
)

// CmdInit handles `pay init`.
func CmdInit() {
	if err := InitDB(); err != nil {
		fmt.Fprintf(os.Stderr, "init error: %v\n", err)
		os.Exit(1)
	}
	fmt.Println("ok")
}

// CmdAddEmployee handles `pay add-employee`.
func CmdAddEmployee(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
}

// CmdAddOrder handles `pay add-order`.
func CmdAddOrder(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
}

// CmdEmployees handles `pay employees`.
func CmdEmployees(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
}

// CmdOrders handles `pay orders <employee>`.
func CmdOrders(args []string) {
	_ = args
	fmt.Fprintln(os.Stderr, "not_implemented")
	os.Exit(1)
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
