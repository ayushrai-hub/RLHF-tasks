package manifest

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"offline-search-shard-coherence/internal/fsutil"
	"offline-search-shard-coherence/internal/model"
)

type Snapshot struct {
	Path          string
	Dir           string
	Manifest      model.Manifest
	CanonicalPath string
	RobotsPath    string
}

func Load(path string) (Snapshot, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return Snapshot{}, err
	}
	var m model.Manifest
	if err := json.Unmarshal(b, &m); err != nil {
		return Snapshot{}, fmt.Errorf("manifest: %w", err)
	}
	dir := filepath.Dir(path)
	return Snapshot{
		Path:          filepath.Clean(path),
		Dir:           dir,
		Manifest:      m,
		CanonicalPath: fsutil.RelTo(dir, m.Canonical),
		RobotsPath:    fsutil.RelTo(dir, m.Robots),
	}, nil
}

func (s Snapshot) ShardPath(shard model.ShardEntry) string {
	return fsutil.RelTo(s.Dir, shard.Path)
}
