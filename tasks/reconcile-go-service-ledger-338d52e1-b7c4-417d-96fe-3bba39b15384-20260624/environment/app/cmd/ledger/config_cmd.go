package main

import (
	"fmt"
	"os"
	"path/filepath"

	"service-ledger/internal/config"
)

func runCheckConfig(args []string) error {
	if len(args) < 1 {
		return fmt.Errorf("usage: ledger check-config <config.json> --out <path>")
	}
	out := "/app/out/config.normalized.json"
	for i := 1; i < len(args); i++ {
		if args[i] == "--out" && i+1 < len(args) {
			out = args[i+1]
			i++
		}
	}
	cfg, err := config.LoadAndNormalize(args[0])
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(out), 0755); err != nil {
		return err
	}
	return config.WriteNormalized(out, cfg)
}
