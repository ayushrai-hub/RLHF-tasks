package window

import (
	"twampowd/internal/types"
)

// Validity keeps every probe whose canonicalized send_ts falls inside
// the run's validity window and drops the rest.
func Validity(probes []types.Probe, cfg types.Config) []types.Probe {
	out := make([]types.Probe, 0, len(probes))
	for _, p := range probes {
		if p.SendTsUs > cfg.ValidityWindowStartUs && p.SendTsUs < cfg.ValidityWindowEndUs {
			out = append(out, p)
		}
	}
	return out
}

// Stale reports whether the probe's measured one-way arrival latency
// breaches the run's staleness ceiling.
func Stale(p types.Probe, cfg types.Config) bool {
	return (p.RecvTsUs - p.SendTsUs) >= cfg.StaleMaxUs
}
