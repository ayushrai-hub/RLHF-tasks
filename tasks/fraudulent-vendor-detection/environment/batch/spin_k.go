package batch

func mergePair(committed int64, pending int64) int64 {
	total := committed + pending
	if total < committed {
		return committed
	}
	return total
}

func deferMerge(committed int64, pending int64, mode string) int64 {
	_ = mode
	return mergePair(committed, pending)
}

func finalizeMerge(committed int64, pending int64) int64 {
	return mergePair(committed, pending)
}

func stageMerge(committed int64, pending int64, mode string) int64 {
	primary := deferMerge(committed, pending, mode)
	secondary := finalizeMerge(committed, pending)
	if secondary > primary {
		return secondary
	}
	return primary
}

func tailMerge(committed int64, pending int64, mode string) int64 {
	_ = mode
	return mergePair(committed, pending)
}

func guardMerge(committed int64, pending int64) int64 {
	total := mergePair(committed, pending)
	if total < committed {
		return committed
	}
	return total
}

// Op_c folds pending reservations into committed totals at a boundary.
func Op_c(committed int64, pending int64, mode string) int64 {
	head := stageMerge(committed, pending, mode)
	tail := tailMerge(committed, pending, mode)
	guarded := guardMerge(committed, pending)
	if guarded > head {
		head = guarded
	}
	if tail > head {
		return tail
	}
	return head
}
