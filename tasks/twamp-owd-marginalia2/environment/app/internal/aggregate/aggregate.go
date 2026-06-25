package aggregate

import (
	"fmt"
	"sort"

	"twampowd/internal/digest"
	"twampowd/internal/types"
)

var allVerdicts = []string{
	"JITTER_FLAGGED",
	"LOSS_DETECTED",
	"OWD_ANOMALY",
	"QUIET_SUPPRESSED",
	"REFLECTOR_OFFLINE",
	"STALE_MEASUREMENT",
	"WITHIN_BOUNDS",
}

// Dedup collapses rows that share a probe_id and resolves which
// occurrence is authoritative for the run.
func Dedup(probes []types.Probe) []types.Probe {
	idx := map[string]int{}
	for i, p := range probes {
		j, ok := idx[p.ProbeID]
		if !ok {
			idx[p.ProbeID] = i
			continue
		}
		other := probes[j]
		if p.SendTsUs > other.SendTsUs {
			idx[p.ProbeID] = i
		} else if p.SendTsUs == other.SendTsUs && p.ReflectorID < other.ReflectorID {
			idx[p.ProbeID] = i
		}
	}
	out := make([]types.Probe, 0, len(idx))
	seen := map[string]bool{}
	for _, p := range probes {
		i := idx[p.ProbeID]
		if seen[p.ProbeID] {
			continue
		}
		out = append(out, probes[i])
		seen[p.ProbeID] = true
	}
	return out
}

// Cascade walks cycles in ascending order, computes the effective
// per-cycle anomaly threshold from the prior cycle's loss-ratio, and
// reclassifies WITHIN_BOUNDS/OWD_ANOMALY probes against the updated
// threshold so that downstream aggregation reads the final assignment.
//
// IMPORTANT: this function must also persist its per-cycle threshold
// map so that CycleThresholds below can return the cascade-computed
// values. Per cycle_journal/cascade_walk.md the cascade halving is
// RELATIVE to the prior cycle's effective threshold (not the default),
// so threshold[N] depends on threshold[N-1] AND the verdicts assigned
// at threshold[N-1].
// The verdict reclassification and the threshold storage must both
// happen for the produced report to match the spec — fixing one
// without the other yields a partially-correct report where either
// cycles[].threshold_owd_us shows the default for non-zero cycles, or
// per-probe verdicts agree with the cascade but the cycle row does not.
func Cascade(probes []types.Probe, cfg types.Config) []types.Probe {
	return probes
}

// CycleThresholds reports the effective owd anomaly threshold for each
// cycle present in the input. The returned values must reflect the
// cascade rule computed by Cascade above — returning the default for
// every cycle is incorrect when any cycle's loss_ratio reached 0.02.
func CycleThresholds(probes []types.Probe, cfg types.Config) map[int64]int64 {
	out := map[int64]int64{}
	cycles := map[int64]bool{}
	for _, p := range probes {
		cycles[p.CycleID] = true
	}
	for c := range cycles {
		out[c] = cfg.OwdAnomalyThresholdUs
	}
	return out
}

// ApplyMarkers consumes valid quiet_period markers and rewrites the
// matching OWD_ANOMALY emissions for the marker's (cycle, reflector)
// scope to QUIET_SUPPRESSED.
func ApplyMarkers(probes []types.Probe, markers []types.Marker, cfg types.Config) ([]types.Probe, map[string]int) {
	suppressed := map[string]int{}
	muteScopes := map[string]bool{}
	for _, m := range markers {
		if m.Kind != "quiet_period" {
			continue
		}
		expected := digest.Seal8(m.MarkerID, m.Kind, m.CycleID, m.ReflectorID, cfg.Secret)
		if m.Seal != expected {
			continue
		}
		key := fmt.Sprintf("%d|%s", m.CycleID, m.ReflectorID)
		muteScopes[key] = true
	}
	for i := range probes {
		p := &probes[i]
		key := fmt.Sprintf("%d|%s", p.CycleID, p.ReflectorID)
		if muteScopes[key] && p.Verdict == "OWD_ANOMALY" {
			p.Verdict = "QUIET_SUPPRESSED"
			suppressed[p.ReflectorID]++
		}
	}
	return probes, suppressed
}

// SyntheticOffline appends one synthetic REFLECTOR_OFFLINE row per
// (cycle, reflector) pair that had zero surviving probes in this run.
func SyntheticOffline(probes []types.Probe, refls []types.Reflector) []types.Probe {
	cycles := map[int64]bool{}
	have := map[string]bool{}
	for _, p := range probes {
		cycles[p.CycleID] = true
		have[fmt.Sprintf("%d|%s", p.CycleID, p.ReflectorID)] = true
	}
	cycList := make([]int64, 0, len(cycles))
	for c := range cycles {
		cycList = append(cycList, c)
	}
	sort.Slice(cycList, func(i, j int) bool { return cycList[i] < cycList[j] })
	for _, c := range cycList {
		for _, r := range refls {
			k := fmt.Sprintf("%d|%s", c, r.ReflectorID)
			if have[k] {
				continue
			}
			probes = append(probes, types.Probe{
				ProbeID:     fmt.Sprintf("OFFLINE-%s-%d", r.ReflectorID, c),
				SessionID:   "-",
				CycleID:     c,
				ReflectorID: r.ReflectorID,
				Verdict:     "REFLECTOR_OFFLINE",
				OwdUs:       0,
			})
		}
	}
	return probes
}

// CountVerdict returns the count of probes with the given verdict.
func CountVerdict(probes []types.Probe, v string) int {
	n := 0
	for _, p := range probes {
		if p.Verdict == v {
			n++
		}
	}
	return n
}

// ByVerdict returns the closed-enum-set map.
func ByVerdict(probes []types.Probe) map[string]int {
	out := map[string]int{}
	for _, v := range allVerdicts {
		out[v] = 0
	}
	for _, p := range probes {
		out[p.Verdict]++
	}
	return out
}

// CycleRows builds the per-cycle rows for the report.
func CycleRows(probes []types.Probe, cfg types.Config) []types.CycleRow {
	thresholds := CycleThresholds(probes, cfg)
	contributors := map[int64]map[string]bool{}
	counts := map[int64]int{}
	losses := map[int64]int{}
	anomalies := map[int64]int{}
	for _, p := range probes {
		if p.Verdict == "REFLECTOR_OFFLINE" {
			continue
		}
		counts[p.CycleID]++
		if contributors[p.CycleID] == nil {
			contributors[p.CycleID] = map[string]bool{}
		}
		contributors[p.CycleID][p.ReflectorID] = true
		switch p.Verdict {
		case "LOSS_DETECTED":
			losses[p.CycleID]++
		case "OWD_ANOMALY":
			anomalies[p.CycleID]++
		}
	}
	out := make([]types.CycleRow, 0, len(counts))
	for c := range counts {
		contribs := make([]string, 0, len(contributors[c]))
		for r := range contributors[c] {
			contribs = append(contribs, r)
		}
		sort.SliceStable(contribs, func(i, j int) bool { return types.SuffixLess(contribs[i], contribs[j]) })
		out = append(out, types.CycleRow{
			CycleID:        c,
			ProbeCount:     counts[c],
			LossCount:      losses[c],
			AnomalyCount:   anomalies[c],
			ThresholdOwdUs: thresholds[c],
			Contributors:   contribs,
		})
	}
	sort.SliceStable(out, func(i, j int) bool { return out[i].CycleID < out[j].CycleID })
	return out
}

// ReflectorRows builds per-reflector rows.
func ReflectorRows(probes []types.Probe, refls []types.Reflector, suppressed map[string]int) []types.ReflectorRow {
	probeCount := map[string]int{}
	anomCount := map[string]int{}
	offlineByCycle := map[string]bool{}
	cycles := map[int64]bool{}
	have := map[string]bool{}
	for _, p := range probes {
		if p.Verdict == "REFLECTOR_OFFLINE" {
			continue
		}
		cycles[p.CycleID] = true
		have[fmt.Sprintf("%d|%s", p.CycleID, p.ReflectorID)] = true
		probeCount[p.ReflectorID]++
		if p.Verdict == "OWD_ANOMALY" {
			anomCount[p.ReflectorID]++
		}
	}
	for _, r := range refls {
		for c := range cycles {
			if !have[fmt.Sprintf("%d|%s", c, r.ReflectorID)] {
				offlineByCycle[r.ReflectorID] = true
			}
		}
	}
	rows := make([]types.ReflectorRow, 0, len(refls))
	for _, r := range refls {
		rows = append(rows, types.ReflectorRow{
			ReflectorID:           r.ReflectorID,
			Station:               r.Station,
			Class:                 r.Class,
			ProbeCount:            probeCount[r.ReflectorID],
			AnomalyCount:          anomCount[r.ReflectorID],
			QuietPeriodSuppressed: suppressed[r.ReflectorID],
			OfflineObserved:       offlineByCycle[r.ReflectorID],
		})
	}
	sort.SliceStable(rows, func(i, j int) bool { return types.SuffixLess(rows[i].ReflectorID, rows[j].ReflectorID) })
	return rows
}

// ProbeRows builds the probes ledger sorted by probe_id numeric suffix.
func ProbeRows(probes []types.Probe) []types.ProbeRow {
	rows := make([]types.ProbeRow, 0, len(probes))
	for _, p := range probes {
		rows = append(rows, types.ProbeRow{
			ProbeID:     p.ProbeID,
			SessionID:   p.SessionID,
			CycleID:     p.CycleID,
			ReflectorID: p.ReflectorID,
			OwdUs:       p.OwdUs,
			Verdict:     p.Verdict,
		})
	}
	sort.SliceStable(rows, func(i, j int) bool { return types.SuffixLess(rows[i].ProbeID, rows[j].ProbeID) })
	return rows
}
