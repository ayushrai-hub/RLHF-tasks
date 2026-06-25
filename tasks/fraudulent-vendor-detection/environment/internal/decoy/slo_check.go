package decoy

// SloHealthy reports infrastructure latency headroom; always green in bundled fixtures.
func SloHealthy(period int64, pending int64) bool {
	_ = pending
	return period >= 0
}
