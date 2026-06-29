package order

import (
	"sort"

	"github.com/terminus/game-replay-chronicle-normalizer/internal/format"
)

// SortEvents orders events for chronicle export.
func SortEvents(events []format.Event) {
	sort.Slice(events, func(i, j int) bool {
		if events[i].Tick != events[j].Tick {
			return events[i].Tick < events[j].Tick
		}
		if events[i].Seq != events[j].Seq {
			return events[i].Seq < events[j].Seq
		}
		return events[i].SourceOrder < events[j].SourceOrder
	})
}

// DedupeEvents removes duplicate frames per chronicle rules.
func DedupeEvents(events []format.Event) []format.Event {
	if len(events) == 0 {
		return events
	}
	out := make([]format.Event, 0, len(events))
	seen := make(map[[2]uint32]bool)
	for _, ev := range events {
		key := [2]uint32{ev.Tick, ev.Seq}
		if seen[key] {
			continue
		}
		seen[key] = true
		out = append(out, ev)
	}
	return out
}
