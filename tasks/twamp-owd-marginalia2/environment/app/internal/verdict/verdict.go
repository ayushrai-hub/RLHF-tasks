package verdict

import (
	"twampowd/internal/types"
	"twampowd/internal/window"
)

// Classify assigns the tentative per-probe verdict from the default
// anomaly threshold, the staleness ceiling, and the loss flag. Later
// passes (Cascade, ApplyMarkers, Jitter) refine the assignment.
func Classify(probes []types.Probe, cfg types.Config) {
	for i := range probes {
		p := &probes[i]
		p.OwdUs = p.RecvMinusSend
		if window.Stale(*p, cfg) {
			p.Verdict = "STALE_MEASUREMENT"
			continue
		}
		if p.LossFlag {
			p.Verdict = "LOSS_DETECTED"
			continue
		}
		if p.OwdUs >= cfg.OwdAnomalyThresholdUs {
			p.Verdict = "OWD_ANOMALY"
			continue
		}
		p.Verdict = "WITHIN_BOUNDS"
	}
}

// Jitter walks each cycle's WITHIN_BOUNDS probes, computes the mean
// owd, and upgrades probes whose absolute deviation breaches the
// configured ceiling.
func Jitter(probes []types.Probe, cfg types.Config) {
	cycSums := map[int64]int64{}
	cycCounts := map[int64]int{}
	for _, p := range probes {
		if p.Verdict == "WITHIN_BOUNDS" {
			cycSums[p.CycleID] += p.OwdUs
			cycCounts[p.CycleID]++
		}
	}
	means := map[int64]int64{}
	for cyc, sum := range cycSums {
		c := cycCounts[cyc]
		if c > 0 {
			means[cyc] = sum / int64(c)
		}
	}
	for i := range probes {
		p := &probes[i]
		if p.Verdict != "WITHIN_BOUNDS" {
			continue
		}
		m, ok := means[p.CycleID]
		if !ok {
			continue
		}
		d := p.OwdUs - m
		if d < 0 {
			d = -d
		}
		if d > cfg.JitterFlagUs {
			p.Verdict = "JITTER_FLAGGED"
		}
	}
}
