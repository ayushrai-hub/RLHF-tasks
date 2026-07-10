package main

import (
	"fmt"
	"os"

	"transitivity-checker/pkg/checker"
	"transitivity-checker/pkg/config"
	"transitivity-checker/pkg/input"
	"transitivity-checker/pkg/output"
)

func main() {
	if len(os.Args) < 3 {
		fmt.Fprintf(os.Stderr, "Usage: %s <rules.json> <output.json>\n", os.Args[0])
		os.Exit(1)
	}

	rulesPath := os.Args[1]
	outputPath := os.Args[2]

	cfg, err := config.LoadWithProfile("config")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Warning: config load error: %v\n", err)
	}

	rules, err := input.ReadRules(rulesPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading rules: %v\n", err)
		os.Exit(1)
	}

	result := checker.CheckTransitivity(rules, cfg)

	if err := output.WriteJSON(result, outputPath); err != nil {
		fmt.Fprintf(os.Stderr, "Error writing output: %v\n", err)
		os.Exit(1)
	}

	fmt.Printf("Analysis complete: %d rules, %d obligations, transitivity_holds=%v\n",
		result.TotalRules, len(result.Obligations), result.TransitivityHolds)
}
