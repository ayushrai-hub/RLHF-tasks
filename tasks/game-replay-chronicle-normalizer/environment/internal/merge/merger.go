package merge

import (
	"os"
	"path/filepath"
	"sort"
	"strings"

	"github.com/terminus/game-replay-chronicle-normalizer/internal/drift"
	"github.com/terminus/game-replay-chronicle-normalizer/internal/format"
	"github.com/terminus/game-replay-chronicle-normalizer/internal/ingest"
	"github.com/terminus/game-replay-chronicle-normalizer/internal/order"
	"github.com/terminus/game-replay-chronicle-normalizer/internal/staging"
)

// NormalizeDir reads all .grsh files from dir and returns chronicle parts.
func NormalizeDir(dir string) ([]format.ShardMeta, []format.Event, error) {
	entries, err := os.ReadDir(dir)
	if err != nil {
		return nil, nil, err
	}
	var paths []string
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		if strings.HasSuffix(strings.ToLower(e.Name()), ".grsh") {
			paths = append(paths, filepath.Join(dir, e.Name()))
		}
	}
	sort.Strings(paths)
	buf := staging.NewBuffer()
	orderCounter := 0
	for _, p := range paths {
		meta, events, err := ingest.LoadShard(p)
		if err != nil {
			return nil, nil, err
		}
		drift.ApplyDrift(meta, events)
		for i := range events {
			events[i].SourceOrder = orderCounter
			orderCounter++
		}
		buf.AppendShard(meta, events)
	}
	shards, all := buf.Snapshot()
	order.SortEvents(all)
	all = order.DedupeEvents(all)
	return shards, all, nil
}
