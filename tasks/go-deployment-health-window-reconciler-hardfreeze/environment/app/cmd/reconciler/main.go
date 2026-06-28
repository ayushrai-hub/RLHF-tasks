package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

const generatedBy = "go-deployment-health-window-reconciler"

type healthReport struct {
	GeneratedBy string         `json:"generated_by"`
	Summary     map[string]int `json:"summary"`
	Windows     []any          `json:"windows"`
}

type warningReport struct {
	GeneratedBy string `json:"generated_by"`
	Warnings    []any  `json:"warnings"`
}

func main() {
	configPath := flag.String("config", "", "config path")
	inputPath := flag.String("input", "", "input directory")
	outPath := flag.String("out", "", "output directory")
	flag.Parse()
	if *configPath == "" || *inputPath == "" || *outPath == "" {
		fmt.Fprintln(os.Stderr, "--config, --input, and --out are required")
		os.Exit(2)
	}
	if err := os.MkdirAll(*outPath, 0o755); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	entries, _ := os.ReadDir(*outPath)
	for _, entry := range entries {
		if !entry.IsDir() && strings.HasSuffix(entry.Name(), ".json") {
			_ = os.Remove(filepath.Join(*outPath, entry.Name()))
		}
	}
	health := healthReport{GeneratedBy: generatedBy, Summary: map[string]int{"deployments_total": 0, "windows_total": 0, "healthy_count": 0, "degraded_count": 0, "failed_count": 0, "rolled_back_count": 0, "warnings_total": 0}, Windows: []any{}}
	warnings := warningReport{GeneratedBy: generatedBy, Warnings: []any{}}
	writeJSON(filepath.Join(*outPath, "health_windows.json"), health)
	writeJSON(filepath.Join(*outPath, "reconciliation_warnings.json"), warnings)
}

func writeJSON(path string, value any) {
	data, err := json.MarshalIndent(value, "", "  ")
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	data = append(data, '\n')
	if err := os.WriteFile(path, data, 0o644); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
