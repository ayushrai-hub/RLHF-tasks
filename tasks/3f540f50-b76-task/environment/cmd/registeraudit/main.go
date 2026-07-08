package main

import (
	"flag"
	"fmt"
	"os"

	"example.com/registeraudit/internal/audit"
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "usage: registeraudit audit ...")
		os.Exit(2)
	}
	switch os.Args[1] {
	case "audit":
		fs := flag.NewFlagSet("audit", flag.ExitOnError)
		dir := fs.String("mreg-dir", "", "directory of register capture shards")
		segment := fs.Int("segment", 0, "target bus segment")
		out := fs.String("json-out", "", "report path")
		_ = fs.Parse(os.Args[2:])
		if *dir == "" || *out == "" {
			fmt.Fprintln(os.Stderr, "mreg-dir and json-out required")
			os.Exit(2)
		}
		if err := audit.Run(*dir, *segment, *out); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	default:
		fmt.Fprintln(os.Stderr, "unknown subcommand")
		os.Exit(2)
	}
}
