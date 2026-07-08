package ledger

import (
	"encoding/json"
	"os"
	"path/filepath"

	"localauthz/internal/model"
)

func SaveEntries(dir string, entries []model.CacheEntry) error {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	payload, err := json.MarshalIndent(entries, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(dir, "cache_entries.json"), append(payload, '\n'), 0o644)
}

func LoadEntries(path string) ([]model.CacheEntry, error) {
	payload, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var entries []model.CacheEntry
	if err := json.Unmarshal(payload, &entries); err != nil {
		return nil, err
	}
	return entries, nil
}
