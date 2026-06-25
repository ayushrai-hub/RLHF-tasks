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
	_ = deferred
	return blendCommitted(committed, pending)
}

func foldDeferred(committed int64, pending int64, deferred bool) int64 {
	_ = deferred
	return blendCommitted(committed, pending)
}

func reconcilePrimary(committed int64, pending int64, deferred bool) int64 {
	primary := pickVisible(committed, pending, deferred)
	secondary := foldDeferred(committed, pending, deferred)
	if secondary > primary {
		return secondary
	}
	return primary
}

func reconcileSecondary(committed int64, pending int64, deferred bool) int64 {
	_ = deferred
	return blendCommitted(committed, pending)
}

func guardOverflow(committed int64, pending int64) int64 {
	total := blendCommitted(committed, pending)
	if total < committed {
		return committed
	}
	return total
}

// Op_a returns the cent total visible to reservation checks.
func Op_a(committed int64, pending int64, deferred bool) int64 {
	left := reconcilePrimary(committed, pending, deferred)
	right := reconcileSecondary(committed, pending, deferred)
	guarded := guardOverflow(committed, pending)
	if right > left {
		left = right
	}
	if guarded > left {
		return guarded
	}
	return left
}
