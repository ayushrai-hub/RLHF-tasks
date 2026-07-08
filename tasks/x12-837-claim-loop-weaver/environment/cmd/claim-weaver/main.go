package main

import (
	"os"

	"claim-weaver/internal/export"
	"claim-weaver/internal/ingest"
	"claim-weaver/internal/report"
	"claim-weaver/internal/staging"
)

const (
	shardsDir    = "/app/data/shards"
	manifestPath = "/app/data/shard-manifest.json"
)

func main() {
	if len(os.Args) < 2 {
		runAll()
		return
	}
	switch os.Args[1] {
	case "ingest":
		runIngest()
	case "export":
		runExport()
	default:
		os.Exit(2)
	}
}

func runAll() {
	if err := os.MkdirAll("/app/output", 0755); err != nil {
		os.Exit(2)
	}
	if err := os.MkdirAll("/app/state", 0755); err != nil {
		os.Exit(2)
	}
	snap, err := ingest.Run(shardsDir, manifestPath)
	if err != nil {
		os.Exit(2)
	}
	if err := ingest.PersistState(snap); err != nil {
		os.Exit(2)
	}
	writeOutputs(snap)
}

func runIngest() {
	if err := os.MkdirAll("/app/state", 0755); err != nil {
		os.Exit(2)
	}
	snap, err := ingest.Run(shardsDir, manifestPath)
	if err != nil {
		os.Exit(2)
	}
	if err := ingest.PersistState(snap); err != nil {
		os.Exit(2)
	}
}

func runExport() {
	if err := os.MkdirAll("/app/output", 0755); err != nil {
		os.Exit(2)
	}
	paths := staging.ResolveStatePaths()
	snap, err := staging.Read(paths.Snapshot)
	if err != nil {
		os.Exit(2)
	}
	writeOutputs(snap)
}

func writeOutputs(snap staging.WeaveSnapshot) {
	woven, summary := export.Publish(snap)
	if err := report.WriteOutputs(
		"/app/output/woven-claims.json",
		"/app/output/weave-summary.json",
		woven,
		summary,
	); err != nil {
		os.Exit(2)
	}
	if err := report.WriteErrors("/app/output/errors.log", snap.Errors); err != nil {
		os.Exit(2)
	}
	if summary.SkippedSegments > 0 {
		os.Exit(1)
	}
}
