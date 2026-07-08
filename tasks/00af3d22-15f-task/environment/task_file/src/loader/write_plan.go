package loader

import (
	"encoding/json"
	"os"
	"path/filepath"

	"tabsettle/model"
)

// WritePlan serializes the plan to path (creating parent directories) as
// indented JSON.
func WritePlan(path string, plan model.Plan) error {
	if dir := filepath.Dir(path); dir != "" {
		if err := os.MkdirAll(dir, 0o755); err != nil {
			return err
		}
	}
	b, err := json.MarshalIndent(plan, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, b, 0o644)
}
