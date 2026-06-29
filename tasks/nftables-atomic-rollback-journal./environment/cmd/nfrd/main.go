package main

import (
	"flag"
	"fmt"
	"os"

	"nfrd.local/nfrd/cli"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: nfrd audit --profile <name>")
		os.Exit(2)
	}
	if os.Args[1] != "audit" {
		fmt.Fprintln(os.Stderr, "unknown command")
		os.Exit(2)
	}
	fs := flag.NewFlagSet("audit", flag.ExitOnError)
	profile := fs.String("profile", "", "profile name")
	_ = fs.Parse(os.Args[2:])
	if *profile == "" {
		fmt.Fprintln(os.Stderr, "profile required")
		os.Exit(2)
	}
	cli.RunAudit(*profile)
}
