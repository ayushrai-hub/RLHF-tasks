package main

import (
	"fmt"
	"os"

	"quotaledger/internal/audit"
	"quotaledger/internal/checkpoint"
	"quotaledger/internal/journal"
	"quotaledger/internal/projection"
)

func main() {
	if len(os.Args) < 2 {
		fail("usage: ledgerctl <import|rebuild|checkpoint|report|audit> ...")
	}
	root := "/app"
	switch os.Args[1] {
	case "import":
		runImport(root, os.Args[2:])
	case "rebuild":
		runRebuild(root)
	case "checkpoint":
		runCheckpoint(root)
	case "report":
		runReport(root, os.Args[2:])
	case "audit":
		runAudit(root, os.Args[2:])
	default:
		fail("unknown command")
	}
}

func runImport(root string, args []string) {
	batch, events := flagPair(args, "--batch", "--events")
	if batch == "" || events == "" {
		fail("import requires --batch and --events")
	}
	imported, err := journal.ImportBatch(root, batch, events)
	if err != nil {
		fail(err.Error())
	}
	if !imported {
		fmt.Println("batch already imported")
		return
	}
	fmt.Printf("imported batch %s\n", batch)
}

func runRebuild(root string) {
	if _, err := projection.Rebuild(root); err != nil {
		fail(err.Error())
	}
	fmt.Println("rebuild complete")
}

func runCheckpoint(root string) {
	snap, err := projection.Load(root)
	if err != nil {
		fail("projection missing; run rebuild first")
	}
	cp, err := checkpoint.Load(root)
	if err != nil {
		fail(err.Error())
	}
	cp.ProjectionDigest = snap.SnapshotDigest
	lines, _, _, err := journal.ReadAllEvents(root)
	if err != nil {
		fail(err.Error())
	}
	cp.JournalSeq = len(lines)
	if err := checkpoint.Save(root, cp); err != nil {
		fail(err.Error())
	}
	fmt.Println("checkpoint saved")
}

func runReport(root string, args []string) {
	out := flagValue(args, "--out")
	if out == "" {
		fail("report requires --out")
	}
	if err := projection.WriteReport(root, out); err != nil {
		fail(err.Error())
	}
}

func runAudit(root string, args []string) {
	out := flagValue(args, "--out")
	if out == "" {
		fail("audit requires --out")
	}
	if err := audit.Write(root, out); err != nil {
		fail(err.Error())
	}
}

func flagPair(args []string, k1, k2 string) (string, string) {
	return flagValue(args, k1), flagValue(args, k2)
}

func flagValue(args []string, key string) string {
	for i := 0; i+1 < len(args); i++ {
		if args[i] == key {
			return args[i+1]
		}
	}
	return ""
}

func fail(msg string) {
	fmt.Fprintln(os.Stderr, msg)
	os.Exit(1)
}
