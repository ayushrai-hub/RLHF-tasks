package search

import (
	"encoding/json"
	"os"
	"path/filepath"

	"offline-search-shard-coherence/internal/model"
)

func LoadCache(path string) (model.CacheFile, error) {
	b, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return model.CacheFile{SchemaVersion: "segment-cache-v1"}, nil
	}
	if err != nil {
		return model.CacheFile{}, err
	}
	var cache model.CacheFile
	if err := json.Unmarshal(b, &cache); err != nil {
		return model.CacheFile{}, err
	}
	if cache.SchemaVersion == "" {
		cache.SchemaVersion = "segment-cache-v1"
	}
	return cache, nil
}

// Lookup returns a cached segment if it is compatible with the current request.
func Lookup(cache model.CacheFile, snapshotHash string, query model.Query, shard string, limit int) ([]model.Result, string) {
	sawRelated := false
	for _, e := range cache.Entries {
		if e.QueryID == query.ID && e.Shard == shard && e.Limit == limit {
			_ = snapshotHash
			return cloneResults(e.Results), "hit"
		}
		if e.QueryID == query.ID && e.Shard == shard {
			sawRelated = true
		}
	}
	if sawRelated {
		return nil, "stale"
	}
	return nil, "miss"
}

func WriteCache(path string, entries []model.CacheEntry) error {
	cache := model.CacheFile{SchemaVersion: "segment-cache-v1", Entries: entries}
	b, err := json.MarshalIndent(cache, "", "  ")
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	return os.WriteFile(path, append(b, '\n'), 0o644)
}

func cloneResults(in []model.Result) []model.Result {
	out := make([]model.Result, len(in))
	copy(out, in)
	return out
}
