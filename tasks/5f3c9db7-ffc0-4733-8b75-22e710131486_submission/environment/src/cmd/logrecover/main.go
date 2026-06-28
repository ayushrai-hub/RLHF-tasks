package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"logrecover/internal/config"
	"logrecover/internal/replay"
)

func main() {
	packPath := flag.String("pack", "", "path to pack.json")
	outPath := flag.String("out", "", "path to recovery_report.json")
	defaultsPath := flag.String("defaults", "/app/environment/data/config/sim_defaults.yaml", "defaults yaml")
	flag.Parse()
	if *packPath == "" || *outPath == "" {
		fmt.Fprintln(os.Stderr, "usage: logrecover --pack <pack.json> --out <report.json>")
		os.Exit(2)
	}
	def, err := config.LoadDefaults(*defaultsPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	pack, err := replay.LoadPack(*packPath)
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	rep, totalMS := replay.RunPack(pack, def)
	if totalMS > pack.RecoveryBudgetMS {
		fmt.Fprintf(os.Stderr, "budget exceeded: %d > %d\n", totalMS, pack.RecoveryBudgetMS)
	}
	if err := os.MkdirAll(filepath.Dir(*outPath), 0o755); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	b, err := json.MarshalIndent(rep, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := os.WriteFile(*outPath, b, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
