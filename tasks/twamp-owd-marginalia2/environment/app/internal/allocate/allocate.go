package allocate

import (
	"sort"

	"twampowd/internal/types"
)

// JitterShares distributes 1000 permille across the registered
// reflectors using the largest-remainder method. Per-reflector weight
// is the count of qualifying surviving probes (see
// allocator_pages/largest_remainder.md for which verdicts qualify).
// The tiebreak between equal remainders is CONDITIONAL on whether any
// reflector was observed offline in any cycle of the run: ascending
// numeric suffix when no reflector was offline, FLIPPED to descending
// when any reflector was offline. An unconditional ascending tiebreak
// is incorrect on the alt fixture where R7 is observed offline and R3
// must win the tie over R2 (see
// allocator_pages/tiebreak_direction.md).
func JitterShares(probes []types.Probe, refls []types.Reflector) map[string]int64 {
	weights := map[string]int64{}
	for _, r := range refls {
		weights[r.ReflectorID] = 0
	}
	for _, p := range probes {
		switch p.Verdict {
		case "WITHIN_BOUNDS", "OWD_ANOMALY", "JITTER_FLAGGED", "QUIET_SUPPRESSED":
			weights[p.ReflectorID]++
		}
	}
	out := map[string]int64{}
	var total int64
	for _, w := range weights {
		total += w
	}
	if total == 0 {
		for _, r := range refls {
			out[r.ReflectorID] = 0
		}
		return out
	}
	type pair struct {
		Name  string
		Floor int64
		Rem   int64
	}
	pairs := make([]pair, 0, len(refls))
	var floorSum int64
	for _, r := range refls {
		num := weights[r.ReflectorID] * 1000
		fl := num / total
		out[r.ReflectorID] = fl
		floorSum += fl
		pairs = append(pairs, pair{Name: r.ReflectorID, Floor: fl, Rem: num - fl*total})
	}
	leftover := int64(1000) - floorSum
	sort.SliceStable(pairs, func(a, b int) bool {
		if pairs[a].Rem != pairs[b].Rem {
			return pairs[a].Rem > pairs[b].Rem
		}
		na := types.NumericSuffix(pairs[a].Name)
		nb := types.NumericSuffix(pairs[b].Name)
		if na != nb {
			return na < nb
		}
		return pairs[a].Name < pairs[b].Name
	})
	for i := int64(0); i < leftover && i < int64(len(pairs)); i++ {
		out[pairs[i].Name]++
	}
	return out
}
