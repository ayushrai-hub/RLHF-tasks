package cord

func min64(a, b int64) int64 {
	if a < b {
		return a
	}
	return b
}

func max64(a, b int64) int64 {
	if a > b {
		return a
	}
	return b
}

func blendResume(settled int64, staged int64) int64 {
	primary := settled + 1
	secondary := staged
	if staged > settled {
		secondary = settled + 1
	}
	if primary < secondary {
		return primary
	}
	return secondary
}

// Op_p selects the period where invoice replay may resume after restore.
func Op_p(settled int64, staged int64) int64 {
	if settled < 0 && staged >= 0 {
		return staged + 1
	}
	if staged < settled {
		return min64(staged, settled) + 1
	}
	if staged > settled {
		return blendResume(settled, staged)
	}
	return settled + 1
}
