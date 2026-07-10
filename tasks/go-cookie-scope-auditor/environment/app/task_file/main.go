package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	policy := flag.String("policy", "", "policy JSON path")
	events := flag.String("events", "", "events JSONL path")
	output := flag.String("output", "", "report JSON path")
	flag.Parse()
	if *policy == "" || *events == "" || *output == "" {
		fmt.Fprintln(os.Stderr, "usage: cookie-auditor --policy policy.json --events events.jsonl --output report.json")
		os.Exit(2)
	}
	fmt.Fprintln(os.Stderr, "cookie auditor is not implemented yet")
	os.Exit(1)
}
