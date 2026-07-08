package main

import (
	"fmt"
	"os"

	"tabsettle/cli"
	"tabsettle/loader"
	"tabsettle/report"
	"tabsettle/settle"
)

func main() {
	args, err := cli.Parse(os.Args[1:])
	if err != nil {
		fmt.Fprintln(os.Stderr, "argument error:", err)
		os.Exit(2)
	}

	participants, err := loader.ReadParticipants(args.Participants)
	if err != nil {
		fmt.Fprintln(os.Stderr, "failed to read participants:", err)
		os.Exit(1)
	}
	rules, err := loader.ReadRules(args.Rules)
	if err != nil {
		fmt.Fprintln(os.Stderr, "failed to read rules:", err)
		os.Exit(1)
	}

	plan := settle.Settle(participants, rules)

	if err := settle.Validate(participants, rules, plan); err != nil {
		fmt.Fprintln(os.Stderr, "warning: plan is not valid:", err)
	}

	if err := loader.WritePlan(args.Out, plan); err != nil {
		fmt.Fprintln(os.Stderr, "failed to write plan:", err)
		os.Exit(1)
	}

	report.Print(os.Stderr, report.Summarize(participants, plan))
	fmt.Printf("wrote %d transfers for %d participants to %s\n",
		len(plan.Transfers), len(participants), args.Out)
}
