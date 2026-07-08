package session

import (
	"encoding/json"
	"os"

	"gradlab/internal/paths"
)

type Checkpoint struct {
	Waterline   int    `json:"waterline"`
	Fingerprint string `json:"fingerprint"`
	GraphSet    string `json:"graph_set"`
}

func LoadCheckpoint() Checkpoint {
	b, err := os.ReadFile(paths.CheckpointPath)
	if err != nil {
		return Checkpoint{}
	}
	var c Checkpoint
	_ = json.Unmarshal(b, &c)
	return c
}

func SaveCheckpoint(c Checkpoint) error {
	_ = os.MkdirAll(paths.VarDir, 0o755)
	b, _ := json.MarshalIndent(c, "", "  ")
	return os.WriteFile(paths.CheckpointPath, append(b, '\n'), 0o644)
}
