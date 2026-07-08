package manifest

import (
	"encoding/json"
	"os"
	"path/filepath"
)

const SchemaVersion = 1

type RunManifest struct {
	SchemaVersion  int    `json:"schema_version"`
	CaseDigest     string `json:"case_digest"`
	CompletedStep  int    `json:"completed_step"`
	HeadRevision   int    `json:"head_revision"`
	RefreshEpoch   int    `json:"refresh_epoch"`
	LastAccepted   bool   `json:"last_refresh_accepted"`
}

func Path(dir string) string {
	return filepath.Join(dir, "run_manifest.json")
}

func Load(dir string) (RunManifest, bool, error) {
	path := Path(dir)
	payload, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return RunManifest{}, false, nil
		}
		return RunManifest{}, false, err
	}
	var m RunManifest
	if err := json.Unmarshal(payload, &m); err != nil {
		return RunManifest{}, false, err
	}
	return m, true, nil
}

func Save(dir string, m RunManifest) error {
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	m.SchemaVersion = SchemaVersion
	payload, err := json.MarshalIndent(m, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(Path(dir), append(payload, '\n'), 0o644)
}
