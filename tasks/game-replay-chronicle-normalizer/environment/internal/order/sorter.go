package order

import (
	"sort"

	"github.com/terminus/game-replay-chronicle-normalizer/internal/format"
)

// SortEvents orders events for chronicle export.
func SortEvents(events []format.Event) {
	sort.Slice(events, func(i, j int) bool {
		return events[i].Seq < events[j].Seq
	})
}

// DedupeEvents removes duplicate frames per chronicle rules.
func DedupeEvents(events []format.Event) []format.Event {
	if len(events) == 0 {
		return events
	}
	out := make([]format.Event, 0, len(events))
	seen := make(map[uint32]bool)
	for _, ev := range events {
		if seen[ev.Tick] {
			continue
		}
		seen[ev.Tick] = true
		out = append(out, ev)
	}
	return out
}
