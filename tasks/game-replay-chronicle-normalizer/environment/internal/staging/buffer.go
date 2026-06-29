package staging

import "github.com/terminus/game-replay-chronicle-normalizer/internal/format"

// Buffer accumulates normalized events before chronicle export.
type Buffer struct {
	Events []format.Event
	Shards []format.ShardMeta
}

// NewBuffer creates an empty staging buffer.
func NewBuffer() *Buffer {
	return &Buffer{}
}

// AppendShard records shard metadata and events after drift correction.
func (b *Buffer) AppendShard(meta format.ShardMeta, events []format.Event) {
	b.Shards = append(b.Shards, meta)
	b.Events = append(b.Events, events...)
}

// Snapshot returns copies of staged shards and events.
func (b *Buffer) Snapshot() ([]format.ShardMeta, []format.Event) {
	shards := append([]format.ShardMeta(nil), b.Shards...)
	events := append([]format.Event(nil), b.Events...)
	return shards, events
}
