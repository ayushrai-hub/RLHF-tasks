package ingest

import (
	"sort"

	"vendorlab/internal/sim"
)

func linesForTick(lines []sim.Invoice, period int64, streamCount int) []sim.Invoice {
	var out []sim.Invoice
	for _, ev := range lines {
		if ev.Tick != period {
			continue
		}
		if ev.Stream < 0 || ev.Stream >= streamCount {
			continue
		}
		out = append(out, ev)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Stream != out[j].Stream {
			return out[i].Stream < out[j].Stream
		}
		return out[i].LineID < out[j].LineID
	})
	return out
}

func ReserveKey(period int64, stage int, id string) string {
	return id
}
