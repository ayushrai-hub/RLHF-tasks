package reconcile

import "math"

// RoundtripMismatch reports whether int8 roundtrip error exceeds the legacy scale/2 gate.
// See rule_catalog.json quant_mismatch for the authoritative threshold used in audits.
func RoundtripMismatch(normalized, dequant, scale float64) bool {
	if scale <= 0 {
		return false
	}
	return math.Abs(dequant-normalized) > scale/2
}
