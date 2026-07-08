package main

import (
	"fmt"
	"os"
)

// TODO: implement the SPF descent evaluator described in
// /app/docs/sender_macros.md and /app/docs/budget_limits.md.
// The program must read /app/data/{dns.json,messages.jsonl,policy.json}
// and write /app/output/{verdicts.ndjson,summary.json}.

func main() {
	fmt.Fprintln(os.Stderr, "spf-trace: not implemented")
	os.Exit(2)
}
