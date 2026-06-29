package main

// Net returns the take-home net in cents for the supplied gross under the
// progressive tax, disposable, and CCPA-pool forward model.
func Net(gross int64) int64 {
	_ = gross
	return 0
}

// Grossup returns the smallest whole-cent gross whose forward Net is at least
// the target, found by bisection over a deterministic integer-cent bracket.
func Grossup(target int64) int64 {
	_ = target
	return 0
}

// TargetGross returns the smallest whole-cent gross whose multi-order net take
// home is at least the target, given the employee's priority-ordered, capped
// garnishment orders. The CCPA pool and the per-order caps both move with the
// gross, so the gross-up bisection wraps the priority allocation at each
// candidate gross.
func TargetGross(target int64, orders []Order) int64 {
	_ = target
	_ = orders
	return 0
}
