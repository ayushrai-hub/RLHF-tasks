package main

import "fmt"

func run(args []string) error {
	if len(args) == 0 {
		return fmt.Errorf("usage: ledger <check-config|summarize|serve> ...")
	}
	switch args[0] {
	case "check-config":
		return runCheckConfig(args[1:])
	case "summarize":
		return runSummarize(args[1:])
	case "serve":
		return runServe(args[1:])
	default:
		return fmt.Errorf("unknown command %q", args[0])
	}
}
