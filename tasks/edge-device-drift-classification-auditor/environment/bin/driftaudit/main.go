package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"edgedrift/engine/reconcile"
)

type manifest struct {
	Scenarios []string `json:"scenarios"`
}

func main() {
	fixturesDir := "/app/fixtures"
	outPath := "/app/build/drift_audit_report.json"

	raw, err := os.ReadFile(filepath.Join(fixturesDir, "manifest.json"))
	if err != nil {
		fmt.Fprintf(os.Stderr, "read manifest: %v\n", err)
		os.Exit(1)
	}
	var man manifest
	if err := json.Unmarshal(raw, &man); err != nil {
		fmt.Fprintf(os.Stderr, "parse manifest: %v\n", err)
		os.Exit(1)
	}

	report := reconcile.Report{Scenarios: make([]reconcile.ScenarioOut, 0, len(man.Scenarios))}
	for _, id := range man.Scenarios {
		path := filepath.Join(fixturesDir, id+".json")
		sc, err := reconcile.LoadScenario(path)
		if err != nil {
			fmt.Fprintf(os.Stderr, "load %s: %v\n", path, err)
			os.Exit(1)
		}
		report.Scenarios = append(report.Scenarios, reconcile.Analyze(sc))
	}

	if err := os.MkdirAll(filepath.Dir(outPath), 0o755); err != nil {
		fmt.Fprintf(os.Stderr, "mkdir: %v\n", err)
		os.Exit(1)
	}
	enc, err := json.Marshal(report)
	if err != nil {
		fmt.Fprintf(os.Stderr, "marshal: %v\n", err)
		os.Exit(1)
	}
	out := append(enc, '\n')
	if err := os.WriteFile(outPath, out, 0o644); err != nil {
		fmt.Fprintf(os.Stderr, "write: %v\n", err)
		os.Exit(1)
	}
}
