package coalesce

import (
	"sort"

	"qack/internal/load"
	"qack/internal/policy"
	"qack/internal/window"
)

// Verdict enum (closed set of 7).
const (
	VerdictDelivered  = "ACK_DELIVERED"
	VerdictCoalesced  = "ACK_COALESCED"
	VerdictReordered  = "ACK_REORDERED"
	VerdictBudget     = "BUDGET_EXCEEDED"
	VerdictTypeInv    = "TYPE_INVALID"
	VerdictBadSpace   = "BAD_SPACE"
	VerdictResetVoid  = "RESET_VOID"
)

func AllVerdicts() []string {
	return []string{
		VerdictCoalesced,
		VerdictDelivered,
		VerdictReordered,
		VerdictBadSpace,
		VerdictBudget,
		VerdictResetVoid,
		VerdictTypeInv,
	}
}

// Event is the classified row that goes into the output.
type Event struct {
	Frame   load.Frame
	Anchor  bool
	Verdict string
}

// Classify produces per-frame initial verdicts, then runs anchor selection +
// window classification per (conn, pn_space, day) bucket, then the F5.6
// cross-cycle cascade.
func Classify(frames []load.Frame, markers []load.Marker, p *policy.Policy, connTier map[string]string) []Event {
	// Build void set from RESET_RANGE markers: (conn -> ranges).
	type rng struct{ lo, hi int64 }
	voidRanges := map[string][]rng{}
	for _, m := range markers {
		if m.Kind != "RESET_RANGE" {
			continue
		}
		voidRanges[m.Conn] = append(voidRanges[m.Conn], rng{m.TargetLow, m.TargetHigh})
	}
	isVoided := func(conn string, pn int64) bool {
		for _, r := range voidRanges[conn] {
			if pn >= r.lo && pn <= r.hi {
				return true
			}
		}
		return false
	}

	events := make([]Event, len(frames))
	for i, fr := range frames {
		ev := Event{Frame: fr}
		switch {
		case fr.TypeInvalid:
			ev.Verdict = VerdictTypeInv
		case !p.IsClosedPnSpace(fr.PnSpace):
			ev.Verdict = VerdictBadSpace
		case isVoided(fr.ConnID, fr.PacketNumber):
			ev.Verdict = VerdictResetVoid
		default:
			ev.Verdict = "" // pending — set by window classification
		}
		events[i] = ev
	}

	// Group pending events by (conn, pn_space, utc_day) and classify within each bucket.
	type key struct {
		conn  string
		pn    string
		day   int64
	}
	groups := map[key][]int{} // group → indices into events
	for i := range events {
		if events[i].Verdict != "" {
			continue
		}
		fr := events[i].Frame
		k := key{fr.ConnID, fr.PnSpace, window.UtcDay(fr.AckTsMs)}
		groups[k] = append(groups[k], i)
	}
	for k, idxs := range groups {
		tier := connTier[k.conn]
		if tier == "" {
			tier = "STANDARD"
		}
		coalesceMs := p.EffectiveCoalesceMs(tier)
		reorderMs := p.EffectiveReorderMs(tier)
		// Anchor: earliest ack_ts; tie → LARGER packet_number; tie → larger shard_seq.
		sort.SliceStable(idxs, func(i, j int) bool {
			a, b := events[idxs[i]].Frame, events[idxs[j]].Frame
			if a.AckTsMs != b.AckTsMs {
				return a.AckTsMs < b.AckTsMs
			}
			if a.PacketNumber != b.PacketNumber {
				return a.PacketNumber > b.PacketNumber
			}
			return a.ShardSeq > b.ShardSeq
		})
		anchorIdx := idxs[0]
		events[anchorIdx].Anchor = true
		events[anchorIdx].Verdict = VerdictDelivered
		anchorTs := events[anchorIdx].Frame.AckTsMs
		for _, idx := range idxs[1:] {
			delta := events[idx].Frame.AckTsMs - anchorTs
			switch {
			case window.Coalesce(delta, coalesceMs):
				events[idx].Verdict = VerdictCoalesced
			case window.Reorder(delta, coalesceMs, reorderMs):
				events[idx].Verdict = VerdictReordered
			default:
				events[idx].Verdict = VerdictDelivered
			}
		}
	}

	// F5.6 cross-cycle cascade.
	applyCascade(events, p.BudgetThreshold)
	return events
}

func isAccepted(v string) bool {
	switch v {
	case VerdictDelivered, VerdictCoalesced, VerdictReordered:
		return true
	}
	return false
}

// applyCascade enforces F5.6: if a (conn, day) bucket has count >= threshold of
// ACCEPTED events, the first eligible event in the SAME conn on the NEXT day
// flips to BUDGET_EXCEEDED. Count is taken BEFORE rewrite.
func applyCascade(events []Event, threshold int64) {
	if threshold <= 0 {
		return
	}
	// Count ACCEPTED per (conn, day).
	type ck struct {
		conn string
		day  int64
	}
	counts := map[ck]int64{}
	for _, ev := range events {
		if !isAccepted(ev.Verdict) {
			continue
		}
		k := ck{ev.Frame.ConnID, window.UtcDay(ev.Frame.AckTsMs)}
		counts[k]++
	}
	// For each connection, sort distinct days asc; for any day whose count >=
	// threshold, the first eligible event of the next-day bucket (any pn_space,
	// earliest ack_ts) flips to BUDGET_EXCEEDED.
	connDays := map[string]map[int64]bool{}
	for k := range counts {
		if connDays[k.conn] == nil {
			connDays[k.conn] = map[int64]bool{}
		}
		connDays[k.conn][k.day] = true
	}
	for conn, daySet := range connDays {
		days := make([]int64, 0, len(daySet))
		for d := range daySet {
			days = append(days, d)
		}
		sort.Slice(days, func(i, j int) bool { return days[i] < days[j] })
		// For each day with breach, find next day with eligible events.
		for i, day := range days {
			if counts[ck{conn, day}] < threshold {
				continue
			}
			if i+1 >= len(days) {
				continue
			}
			nextDay := days[i+1]
			// Find first eligible event (currently ACCEPTED) by ack_ts in nextDay.
			bestIdx := -1
			var bestTs int64
			for idx := range events {
				ev := &events[idx]
				if ev.Frame.ConnID != conn {
					continue
				}
				if window.UtcDay(ev.Frame.AckTsMs) != nextDay {
					continue
				}
				if !isAccepted(ev.Verdict) {
					continue
				}
				if bestIdx == -1 || ev.Frame.AckTsMs < bestTs {
					bestIdx = idx
					bestTs = ev.Frame.AckTsMs
				}
			}
			if bestIdx != -1 {
				events[bestIdx].Verdict = VerdictBudget
				events[bestIdx].Anchor = false
			}
		}
	}
}
