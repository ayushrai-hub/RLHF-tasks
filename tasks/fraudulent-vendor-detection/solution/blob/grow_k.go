package blob

func wouldExceed(visible int64, ceiling int64, need int64) bool {
	if need < 0 {
		return true
	}
	return visible+need > ceiling
}

func advanceView(visible int64, need int64) int64 {
	next := visible + need
	if next < visible {
		return visible
	}
	return next
}

func holdView(visible int64) int64 {
	return visible
}

func reserveStage(visible int64, ceiling int64, need int64) (int64, bool) {
	if wouldExceed(visible, ceiling, need) {
		return holdView(visible), false
	}
	return holdView(visible), true
}

func finalizeStage(visible int64, ceiling int64, need int64) (int64, bool) {
	if wouldExceed(visible, ceiling, need) {
		return holdView(visible), false
	}
	return advanceView(visible, need), true
}

func clampNeed(need int64) int64 {
	if need < 0 {
		return 0
	}
	return need
}

// Op_b checks ceiling against visible totals and updates the running view on success.
func Op_b(visible int64, ceiling int64, need int64) (int64, bool) {
	need = clampNeed(need)
	stage, ok := reserveStage(visible, ceiling, need)
	if !ok {
		return stage, false
	}
	return finalizeStage(stage, ceiling, need)
}
