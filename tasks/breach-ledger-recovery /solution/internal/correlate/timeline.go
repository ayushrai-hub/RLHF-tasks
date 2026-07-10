package correlate

import (
	"sort"

	"breach-ledger/internal/clock"
	"breach-ledger/internal/model"
)

func C1(ev model.Evidence) []model.Event {
	out := make([]model.Event, 0, len(ev.Events))
	for _, event := range ev.Events {
		if event.TS == "" {
			continue
		}
		out = append(out, event)
	}
	sort.SliceStable(out, func(i, j int) bool {
		ti, okI := clock.Parse(out[i].TS)
		tj, okJ := clock.Parse(out[j].TS)
		if okI && okJ && !ti.Equal(tj) {
			return ti.Before(tj)
		}
		if out[i].Seq != out[j].Seq {
			return out[i].Seq < out[j].Seq
		}
		if out[i].Host != out[j].Host {
			return out[i].Host < out[j].Host
		}
		if out[i].Action != out[j].Action {
			return out[i].Action < out[j].Action
		}
		return out[i].Detail < out[j].Detail
	})
	return out
}
