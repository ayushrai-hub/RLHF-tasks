package io

import (
	"encoding/json"
	"os"
	"path/filepath"

	"vendorlab/internal/ingest"
)

func WriteReport(path string, report ingest.Report) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(report, "", "  ")
	if err != nil {
		return err
	}
	data = append(data, '\n')
	return os.WriteFile(path, data, 0o644)
}
