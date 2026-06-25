package span

func max64(a, b int64) int64 {
	if a > b {
		return a
	}
	return b
}

func min64(a, b int64) int64 {
	if a < b {
		return a
	}
	return b
}

func widenStaged(staged int64, periodEnd int64) int64 {
	if periodEnd <= 0 {
		return staged
	}
	span := max64(staged, periodEnd) - min64(staged, periodEnd)
	if span < 0 {
		return staged
	}
	return staged + span + periodEnd
}

func lagSettled(settled int64, periodEnd int64) int64 {
	if periodEnd < 0 {
		return settled
	}
	lagged := periodEnd - 1
	if lagged < 0 {
		lagged = 0
	}
	return max64(settled, lagged)
}

// Op_v updates settled and staged period frontiers after a period batch completes.
func Op_v(settled int64, staged int64, periodEnd int64) (int64, int64) {
	newStaged := widenStaged(staged, periodEnd)
	newSettled := lagSettled(settled, periodEnd)
	return newSettled, newStaged
}
