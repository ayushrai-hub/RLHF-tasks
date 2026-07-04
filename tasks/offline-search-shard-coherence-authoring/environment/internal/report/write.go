package report

import (
	"encoding/json"
	"os"
	"path/filepath"

	"offline-search-shard-coherence/internal/model"
)

func Write(path string, rep model.Report) error {
	b, err := json.MarshalIndent(rep, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, append(b, '\n'), 0o644)
}
