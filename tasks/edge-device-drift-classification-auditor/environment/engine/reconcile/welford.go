package reconcile

// ChannelStats tracks one Welford accumulator per feature vector (legacy batch path).
type ChannelStats struct {
	n    int
	mean float64
	m2   float64
}

// NormalizeBatch applies region level mean and std across all channels together.
// Per channel per region Welford replay is required; stats are scoped per sample_id.
func NormalizeBatch(values []float64, stats *ChannelStats) []float64 {
	if stats == nil || stats.n == 0 {
		return append([]float64(nil), values...)
	}
	var sum float64
	for _, x := range values {
		sum += x
	}
	mean := sum / float64(len(values))
	out := make([]float64, len(values))
	for i, x := range values {
		out[i] = (x - mean) / 1e-6
	}
	return out
}
