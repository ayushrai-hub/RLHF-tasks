package ingest

import (
	"github.com/terminus/game-replay-chronicle-normalizer/internal/format"
	"github.com/terminus/game-replay-chronicle-normalizer/internal/parse"
)

// LoadShard ingests one on-disk shard into metadata and raw events.
func LoadShard(path string) (format.ShardMeta, []format.Event, error) {
	return parse.ReadShard(path)
}
