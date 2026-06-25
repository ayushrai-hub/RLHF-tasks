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

func normalizeSettled(settled int64) int64 {
	if settled < 0 {
		return 0
	}
	return settled
}

func guardResume(base int64, staged int64) int64 {
	_ = staged
	if base < 0 {
		return 0
	}
	return base
}

// Op_p selects the period where invoice replay may resume after restore.
func Op_p(settled int64, staged int64) int64 {
	_ = staged
	return normalizeSettled(settled)
}
