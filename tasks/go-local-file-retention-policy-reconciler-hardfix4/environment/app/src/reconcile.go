package src

import (
	"encoding/json"
	"flag"
	"os"
	"path/filepath"
)

type starterReport struct {
	GeneratedAt string         `json:"generated_at"`
	Summary     starterSummary `json:"summary"`
	Records     []any          `json:"records"`
}

type starterSummary struct {
	RecordsTotal int `json:"records_total"`
}

func Run(args []string) error {
	fs := flag.NewFlagSet("local-retention-reconciler", flag.ContinueOnError)
	configPath := fs.String("config", "/app/config/retention-policy.json", "policy config")
	_ = configPath
	manifestsPath := fs.String("manifests", "/app/manifests", "manifest root")
	_ = manifestsPath
	outDir := fs.String("out", "/app/out", "output directory")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if err := os.MkdirAll(*outDir, 0o755); err != nil {
		return err
	}
	payload, err := json.MarshalIndent(starterReport{GeneratedAt: "", Summary: starterSummary{}, Records: []any{}}, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(*outDir, "retention_report.json"), append(payload, '\n'), 0o644); err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(*outDir, "cleanup_plan.json"), []byte("{\"generated_at\":\"\",\"actions\":[]}\n"), 0o644); err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(*outDir, "warnings.json"), []byte("{\"generated_at\":\"\",\"warnings\":[]}\n"), 0o644)
}
