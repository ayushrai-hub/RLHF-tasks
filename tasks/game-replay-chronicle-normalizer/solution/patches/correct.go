package drift

import "github.com/terminus/game-replay-chronicle-normalizer/internal/format"

// ApplyDrift corrects raw ticks using per-shard drift metadata.
func ApplyDrift(meta format.ShardMeta, events []format.Event) {
	for i := range events {
		raw := int64(events[i].Tick)
		corrected := raw - int64(meta.DriftMs)
		if corrected < 0 {
			corrected = 0
		}
		events[i].Tick = uint32(corrected)
	}
}
