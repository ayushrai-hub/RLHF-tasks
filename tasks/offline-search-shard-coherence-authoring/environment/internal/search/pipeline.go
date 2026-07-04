package search

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"offline-search-shard-coherence/internal/fsutil"
	snap "offline-search-shard-coherence/internal/manifest"
	"offline-search-shard-coherence/internal/model"
	"offline-search-shard-coherence/internal/report"
)

func Run(planPath, outPath string) error {
	plan, err := LoadPlan(planPath)
	if err != nil {
		return err
	}
	snapshot, err := snap.Load(plan.Manifest)
	if err != nil {
		return err
	}
	queries, err := fsutil.ReadJSONL[model.Query](plan.Queries)
	if err != nil {
		return err
	}
	canon, err := LoadCanonical(snapshot.CanonicalPath)
	if err != nil {
		return err
	}
	robots, err := LoadRobots(snapshot.RobotsPath)
	if err != nil {
		return err
	}
	snapshotHash, err := fsutil.SnapshotHash(snapshot.Path, snapshot.Manifest)
	if err != nil {
		return err
	}
	cache, err := LoadCache(plan.Cache)
	if err != nil {
		return err
	}

	rep := model.Report{
		SchemaVersion: "offline-search-run-v1",
		SnapshotID:    snapshot.Manifest.SnapshotID,
		SnapshotHash:  snapshotHash,
		Limit:         plan.Limit,
		Provenance: model.Provenance{
			ManifestPath: snapshot.Path,
			QueryPath:    plan.Queries,
			CachePath:    plan.Cache,
		},
	}
	newEntries := []model.CacheEntry{}
	for _, q := range queries {
		candidates := []model.Result{}
		for _, shard := range snapshot.Manifest.Shards {
			results, status := Lookup(cache, snapshotHash, q, shard.ID, plan.Limit)
			if results == nil {
				results, err = SearchShard(snapshot.ShardPath(shard), shard.ID, q, canon, robots, snapshot.Manifest.FreshnessEpoch)
				if err != nil {
					return err
				}
			}
			candidates = append(candidates, results...)
			rep.Provenance.Segments = append(rep.Provenance.Segments, model.SegmentTrace{
				QueryID:        q.ID,
				Shard:          shard.ID,
				SnapshotHash:   snapshotHash,
				CacheStatus:    status,
				CandidateCount: len(results),
			})
			newEntries = append(newEntries, model.CacheEntry{
				SnapshotHash: snapshotHash,
				QueryID:      q.ID,
				QueryText:    q.Text,
				Shard:        shard.ID,
				Limit:        plan.Limit,
				Results:      results,
			})
		}
		rep.Queries = append(rep.Queries, model.QueryReport{ID: q.ID, Text: q.Text, Results: MergeResults(candidates, plan.Limit)})
	}
	if err := report.Write(outPath, rep); err != nil {
		return err
	}
	return WriteCache(plan.Cache, newEntries)
}

func LoadPlan(path string) (model.Plan, error) {
	b, err := os.ReadFile(path)
	if err != nil {
		return model.Plan{}, err
	}
	var p model.Plan
	if err := json.Unmarshal(b, &p); err != nil {
		return model.Plan{}, err
	}
	if p.Limit <= 0 {
		return model.Plan{}, fmt.Errorf("plan limit must be positive")
	}
	p.Manifest = fsutil.AbsFrom(path, p.Manifest)
	p.Queries = fsutil.AbsFrom(path, p.Queries)
	p.Cache = fsutil.AbsFrom(path, p.Cache)
	p.Manifest = filepath.Clean(p.Manifest)
	p.Queries = filepath.Clean(p.Queries)
	p.Cache = filepath.Clean(p.Cache)
	return p, nil
}
