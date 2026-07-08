package ingest

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"columnarvalidator/codec/types"
)

func fixtureDir() string {
	if d := os.Getenv("COLUMNAR_FIXTURE_DIR"); d != "" {
		return d
	}
	return "/app/fixtures"
}

func LoadAll() ([]types.Segment, error) {
	dir := fixtureDir()
	ids := make([]string, 0, 20)
	for i := 1; i <= 20; i++ {
		ids = append(ids, fmt.Sprintf("segment_%02d", i))
	}
	sort.Strings(ids)

	segments := make([]types.Segment, 0, 20)
	for _, id := range ids {
		path := filepath.Join(dir, id+".json")
		raw, err := os.ReadFile(path)
		if err != nil {
			return nil, err
		}
		var seg types.Segment
		if err := json.Unmarshal(raw, &seg); err != nil {
			return nil, fmt.Errorf("%s: %w", path, err)
		}
		segments = append(segments, seg)
	}
	return segments, nil
}
