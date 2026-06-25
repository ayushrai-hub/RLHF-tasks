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

func syncFrontiers(settled int64, staged int64, periodEnd int64) (int64, int64) {
	newSettled := max64(settled, periodEnd)
	newStaged := max64(staged, periodEnd)
	return newSettled, newStaged
}

func clampStagedToSettled(settled int64, staged int64) int64 {
	if staged > settled {
		return staged
	}
	return settled
}

// Op_v updates settled and staged period frontiers after a period batch completes.
func Op_v(settled int64, staged int64, periodEnd int64) (int64, int64) {
	newSettled, newStaged := syncFrontiers(settled, staged, periodEnd)
	newStaged = clampStagedToSettled(newSettled, newStaged)
	return newSettled, newStaged
}
