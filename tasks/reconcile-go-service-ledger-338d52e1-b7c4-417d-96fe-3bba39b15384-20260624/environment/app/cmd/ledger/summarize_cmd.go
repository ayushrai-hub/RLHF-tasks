package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"service-ledger/internal/config"
	"service-ledger/internal/events"
	"service-ledger/internal/summary"
)

func runSummarize(args []string) error {
	var cfgPath, eventsPath, outPath string
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--config":
			if i+1 >= len(args) {
				return fmt.Errorf("--config requires a path")
			}
			cfgPath = args[i+1]
			i++
		case "--events":
			if i+1 >= len(args) {
				return fmt.Errorf("--events requires a path")
			}
			eventsPath = args[i+1]
			i++
		case "--out":
			if i+1 >= len(args) {
				return fmt.Errorf("--out requires a path")
			}
			outPath = args[i+1]
			i++
		}
	}
	if cfgPath == "" || eventsPath == "" || outPath == "" {
		return fmt.Errorf("usage: ledger summarize --config <config.json> --events <events.jsonl> --out <summary.json>")
	}
	cfg, err := config.LoadAndNormalize(cfgPath)
	if err != nil {
		return err
	}
	records, err := events.ReadJSONL(eventsPath)
	if err != nil {
		return err
	}
	result := summary.Build(cfg, records)
	data, err := json.MarshalIndent(result, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(outPath), 0755); err != nil {
		return err
	}
	return os.WriteFile(outPath, append(data, '\n'), 0644)
}
