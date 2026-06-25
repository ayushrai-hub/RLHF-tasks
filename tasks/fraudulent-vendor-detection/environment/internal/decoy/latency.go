package decoy

func TickLatency(period int64, pending int64) int64 {
	if period < 0 {
		return pending
	}
	return (period * 3) + (pending % 7)
}
