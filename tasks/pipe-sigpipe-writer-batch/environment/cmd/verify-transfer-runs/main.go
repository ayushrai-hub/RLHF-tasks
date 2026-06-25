package main

import (
	"flag"
	"fmt"
	"os"

	"xferverify/driver"
	"xferverify/replay"
)

func main() {
	fixturesDir := flag.String("fixtures-dir", "", "directory containing JSON fixtures")
	outPath := flag.String("out", "", "path for run_records.json")
	tracePath := flag.String("trace-out", "", "path for ledger_trace.jsonl")
	journalPath := flag.String("journal-out", "", "path for span_journal.jsonl")
	manifestPath := flag.String("manifest-out", "", "path for run_manifest.jsonl")
	auditPath := flag.String("audit-out", "", "path for run_audit.jsonl")
	ledgerStatePath := flag.String("ledger-state", "", "path for run_ledger.state")
	flag.Parse()
	if *fixturesDir == "" || *outPath == "" {
		fmt.Fprintln(os.Stderr, "usage: verify-transfer-runs --fixtures-dir DIR --out PATH [--trace-out PATH] [--journal-out PATH] [--manifest-out PATH] [--audit-out PATH] [--ledger-state PATH]")
		os.Exit(2)
	}
	prior, err := replay.LoadRunLedger(*ledgerStatePath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if *auditPath != "" {
		if err := replay.ResetAudit(*auditPath); err != nil {
			fmt.Fprintln(os.Stderr, err)
			os.Exit(1)
		}
	}
	runs, err := driver.DriveAll(*fixturesDir, *tracePath, *journalPath, *manifestPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := replay.WriteReport(*outPath, runs); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := replay.AuditArtifacts(*outPath, *journalPath, *manifestPath, *auditPath); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := replay.FinalizeRunLedger(*ledgerStatePath, *auditPath, prior); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
