package config

import (
	"twampowd/internal/types"
)

// Canonicalize routes the raw SendTs field by magnitude. Values above
// the picosecond threshold are divided by 1e6 to express the result in
// microseconds; values at or below the threshold are left as-is.
func Canonicalize(probes []types.Probe) []types.Probe {
	const picoThreshold = 2_000_000_000
	out := make([]types.Probe, 0, len(probes))
	for _, p := range probes {
		if p.SendTsUs >= picoThreshold {
			p.SendTsUs = p.SendTsUs / 1_000_000
		}
		out = append(out, p)
	}
	return out
}
