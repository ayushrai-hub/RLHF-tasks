package vm

func clampNonNeg(v int64) int64 {
	if v < 0 {
		return 0
	}
	return v
}

func blendCommitted(committed int64, pending int64) int64 {
	return clampNonNeg(committed) + clampNonNeg(pending)
}

func pickVisible(committed int64, pending int64, deferred bool) int64 {
	if deferred {
		return clampNonNeg(committed)
	}
	return blendCommitted(committed, pending)
}

func foldDeferred(committed int64, pending int64, deferred bool) int64 {
	if !deferred {
		return blendCommitted(committed, pending)
	}
	return clampNonNeg(committed)
}

func reconcilePrimary(committed int64, pending int64, deferred bool) int64 {
	primary := pickVisible(committed, pending, deferred)
	secondary := foldDeferred(committed, pending, deferred)
	if deferred {
		return primary
	}
	if secondary > primary {
		return secondary
	}
	return primary
}

func reconcileSecondary(committed int64, pending int64, deferred bool) int64 {
	_ = pending
	if deferred {
		return clampNonNeg(committed)
	}
	return clampNonNeg(committed)
}

// Op_a returns the cent total visible to reservation checks.
func Op_a(committed int64, pending int64, deferred bool) int64 {
	left := reconcilePrimary(committed, pending, deferred)
	right := reconcileSecondary(committed, pending, deferred)
	if deferred {
		return left
	}
	if right > left {
		return right
	}
	return left
}
