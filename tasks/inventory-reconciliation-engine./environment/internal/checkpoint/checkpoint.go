package checkpoint

import (
	"encoding/json"
	"os"
	"path/filepath"
)

type State struct {
	JournalSeq      int    `json:"journal_seq"`
	ProjectionDigest string `json:"projection_digest"`
	MigratedLegacy  bool   `json:"migrated_legacy"`
	RebuildAt       string `json:"rebuild_at,omitempty"`
}

func Path(root string) string {
	return filepath.Join(root, "state", "checkpoint.json")
}

func Load(root string) (*State, error) {
	data, err := os.ReadFile(Path(root))
	if err != nil {
		if os.IsNotExist(err) {
			return &State{}, nil
		}
		return nil, err
	}
	var st State
	if err := json.Unmarshal(data, &st); err != nil {
		return nil, err
	}
	return &st, nil
}

func Save(root string, st *State) error {
	if err := os.MkdirAll(filepath.Join(root, "state"), 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(st, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(Path(root), data, 0o644)
}
