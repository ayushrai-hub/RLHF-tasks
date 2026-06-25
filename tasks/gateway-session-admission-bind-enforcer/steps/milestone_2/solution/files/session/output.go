package session

import (
	"encoding/json"
	"os"
	"path/filepath"
)

func WriteOutput(dir string, out Output) error {
	data, err := json.MarshalIndent(out, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(dir, "output.json"), data, 0o644)
}
