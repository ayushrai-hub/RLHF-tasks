package report

import (
	"encoding/json"
	"os"
	"path/filepath"

	"localauthz/internal/model"
)

func WriteTrace(path string, trace model.Trace) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	trace.Provenance.OutputPath = path
	payload, err := json.MarshalIndent(trace, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(payload, '\n'), 0o644)
}
